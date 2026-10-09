"""
game.py — Bluff Call's game state machine. Pure logic, no networking.

Kept deliberately separate from the Socket.io event layer (events.py) so
the rules (scoring, round progression, who-can-do-what) are testable
without spinning up a server or a client — the thing most likely to have
subtle bugs is the logic itself, not the transport.

Round flow per room:
    lobby -> writing -> voting -> reveal -> (next round: writing, or game_over)

All state is in-memory, keyed by room code. A live game session has nothing
worth persisting past the game ending -- unlike the lead-enrichment agent,
there's no durability requirement here, so a plain in-memory dict is the
right choice, not a shortcut.
"""

import random
import string
from dataclasses import dataclass, field

from app.questions import QUESTIONS

MIN_PLAYERS = 3
MAX_PLAYERS = 10
TOTAL_ROUNDS = 8
WRITE_SECONDS = 45
VOTE_SECONDS = 30
REVEAL_SECONDS = 8
CORRECT_GUESS_POINTS = 1000
FOOLED_VOTE_POINTS = 500


class GameError(ValueError):
    """Raised for any invalid game action (wrong phase, not host, etc.)."""


@dataclass
class Player:
    sid: str
    name: str
    score: int = 0
    connected: bool = True


@dataclass
class AnswerOption:
    text: str
    is_real: bool
    author_sid: str | None  # None for the real answer


@dataclass
class Room:
    code: str
    host_sid: str
    players: dict = field(default_factory=dict)          # sid -> Player
    status: str = "lobby"                                  # lobby/writing/voting/reveal/game_over
    round_num: int = 0
    total_rounds: int = TOTAL_ROUNDS
    used_question_indices: set = field(default_factory=set)
    current_question: dict | None = None
    bluffs: dict = field(default_factory=dict)             # sid -> text
    votes: dict = field(default_factory=dict)               # sid -> option index
    answer_options: list = field(default_factory=list)       # list[AnswerOption]
    round_results: list = field(default_factory=list)         # for the reveal screen

    def alive(self) -> list:
        return [p for p in self.players.values() if p.connected]


_rooms: dict = {}  # module-level registry: room code -> Room


def _generate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity
    while True:
        code = "".join(random.choices(alphabet, k=5))
        if code not in _rooms:
            return code


def create_room(host_sid: str, host_name: str) -> Room:
    code = _generate_code()
    room = Room(code=code, host_sid=host_sid)
    room.players[host_sid] = Player(sid=host_sid, name=host_name)
    _rooms[code] = room
    return room


def get_room(code: str) -> Room | None:
    return _rooms.get((code or "").upper())


def remove_room(code: str) -> None:
    _rooms.pop((code or "").upper(), None)


def join_room(room: Room, sid: str, name: str) -> None:
    if room.status != "lobby":
        raise GameError("This game has already started.")
    if len(room.players) >= MAX_PLAYERS:
        raise GameError("Room is full.")
    if any(p.name.lower() == name.lower() for p in room.players.values()):
        raise GameError("That name is already taken in this room.")
    room.players[sid] = Player(sid=sid, name=name)


def mark_disconnected(room: Room, sid: str) -> None:
    if sid in room.players:
        room.players[sid].connected = False


def start_game(room: Room, requesting_sid: str) -> dict:
    if requesting_sid != room.host_sid:
        raise GameError("Only the host can start the game.")
    if room.status != "lobby":
        raise GameError("Game already started.")
    if len(room.alive()) < MIN_PLAYERS:
        raise GameError(f"Need at least {MIN_PLAYERS} players to start.")
    return next_round(room)


def next_round(room: Room) -> dict:
    """Advance to a new round's writing phase. Returns the question dict."""
    room.round_num += 1
    available = [i for i in range(len(QUESTIONS)) if i not in room.used_question_indices]
    if not available:
        room.used_question_indices.clear()
        available = list(range(len(QUESTIONS)))
    idx = random.choice(available)
    room.used_question_indices.add(idx)

    room.current_question = QUESTIONS[idx]
    room.bluffs = {}
    room.votes = {}
    room.answer_options = []
    room.round_results = []
    room.status = "writing"
    return room.current_question


def submit_bluff(room: Room, sid: str, text: str) -> None:
    if room.status != "writing":
        raise GameError("Not currently accepting answers.")
    if sid not in room.players:
        raise GameError("You're not in this room.")
    text = text.strip()
    if not text:
        raise GameError("Answer can't be empty.")
    room.bluffs[sid] = text[:200]


def all_bluffs_in(room: Room) -> bool:
    return len(room.bluffs) >= len(room.alive())


def start_voting(room: Room) -> list:
    """Build the shuffled answer pool and move to voting. Returns the options
    (without revealing is_real/author -- that's the caller's job to strip
    before broadcasting to clients)."""
    if room.status != "writing":
        raise GameError("Not in the writing phase.")

    options = [AnswerOption(text=room.current_question["a"], is_real=True, author_sid=None)]
    for sid, text in room.bluffs.items():
        options.append(AnswerOption(text=text, is_real=False, author_sid=sid))
    random.shuffle(options)

    room.answer_options = options
    room.votes = {}
    room.status = "voting"
    return options


def submit_vote(room: Room, sid: str, option_index: int) -> None:
    if room.status != "voting":
        raise GameError("Not currently voting.")
    if sid not in room.players:
        raise GameError("You're not in this room.")
    if not (0 <= option_index < len(room.answer_options)):
        raise GameError("Invalid option.")
    if room.answer_options[option_index].author_sid == sid:
        raise GameError("You can't vote for your own answer.")
    room.votes[sid] = option_index


def all_votes_in(room: Room) -> bool:
    # Players who didn't submit a bluff can still vote; everyone alive votes.
    return len(room.votes) >= len(room.alive())


def score_round(room: Room) -> list:
    """Apply scoring for the completed voting phase, return a results summary
    for the reveal screen. Safe to call even if nobody voted/answered."""
    fooled_counts = {opt.author_sid: 0 for opt in room.answer_options if opt.author_sid}
    correct_voters = []

    for voter_sid, option_index in room.votes.items():
        option = room.answer_options[option_index]
        if option.is_real:
            room.players[voter_sid].score += CORRECT_GUESS_POINTS
            correct_voters.append(voter_sid)
        elif option.author_sid in fooled_counts:
            fooled_counts[option.author_sid] += 1

    for author_sid, count in fooled_counts.items():
        if count and author_sid in room.players:
            room.players[author_sid].score += count * FOOLED_VOTE_POINTS

    results = {
        "question": room.current_question["q"],
        "real_answer": room.current_question["a"],
        "options": [
            {
                "text": opt.text,
                "is_real": opt.is_real,
                "author_name": room.players[opt.author_sid].name if opt.author_sid in room.players else None,
                "votes": sum(1 for v in room.votes.values() if v == i),
            }
            for i, opt in enumerate(room.answer_options)
        ],
        "correct_voters": [room.players[s].name for s in correct_voters if s in room.players],
    }
    room.round_results = results
    room.status = "reveal"
    return results


def is_game_over(room: Room) -> bool:
    return room.round_num >= room.total_rounds


def end_game(room: Room) -> list:
    room.status = "game_over"
    return sorted(room.players.values(), key=lambda p: p.score, reverse=True)


def room_snapshot(room: Room) -> dict:
    """A client-safe view of room state (never leaks who authored which bluff
    before reveal, or the real answer before voting closes)."""
    return {
        "code": room.code,
        "status": room.status,
        "round_num": room.round_num,
        "total_rounds": room.total_rounds,
        "host_sid": room.host_sid,
        "players": [
            {"sid": p.sid, "name": p.name, "score": p.score, "connected": p.connected}
            for p in room.players.values()
        ],
    }
