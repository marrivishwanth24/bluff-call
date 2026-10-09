"""
events.py — Socket.io event handlers and the per-room game loop.

One background task per room (started when the host clicks "start") drives
every round sequentially: writing -> voting -> reveal -> next round or game
over. That single coroutine is the only thing that advances room.status, so
there's no race between two different code paths both trying to move the
game forward -- client events (submit_bluff/submit_vote) only ever write
into room.bluffs/room.votes, which the loop polls.
"""

import logging

import socketio

from app import game

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

_sid_to_room: dict[str, str] = {}  # sid -> room code, for disconnect/lookup


def _player_view(room: game.Room) -> list[dict]:
    return [
        {"sid": p.sid, "name": p.name, "score": p.score, "connected": p.connected}
        for p in sorted(room.players.values(), key=lambda p: -p.score)
    ]


async def _emit_error(sid: str, message: str) -> None:
    await sio.emit("game_error", {"message": message}, to=sid)


async def _emit_room_update(room: game.Room) -> None:
    await sio.emit("room_update", game.room_snapshot(room), room=room.code)


@sio.event
async def connect(sid, environ):
    logger.info("connected: %s", sid)


@sio.event
async def disconnect(sid):
    code = _sid_to_room.pop(sid, None)
    if not code:
        return
    room = game.get_room(code)
    if not room:
        return
    game.mark_disconnected(room, sid)
    await _emit_room_update(room)
    logger.info("disconnected: %s from room %s", sid, code)


@sio.event
async def create_room(sid, data):
    name = (data or {}).get("name", "").strip()[:24]
    if not name:
        return await _emit_error(sid, "Enter a name first.")

    room = game.create_room(sid, name)
    _sid_to_room[sid] = room.code
    await sio.enter_room(sid, room.code)
    await sio.emit("room_created", game.room_snapshot(room), to=sid)


@sio.event
async def join_room_event(sid, data):
    code = (data or {}).get("code", "").strip()
    name = (data or {}).get("name", "").strip()[:24]
    if not name:
        return await _emit_error(sid, "Enter a name first.")

    room = game.get_room(code)
    if not room:
        return await _emit_error(sid, "No room found with that code.")

    try:
        game.join_room(room, sid, name)
    except game.GameError as e:
        return await _emit_error(sid, str(e))

    _sid_to_room[sid] = room.code
    await sio.enter_room(sid, room.code)
    await sio.emit("room_joined", game.room_snapshot(room), to=sid)
    await _emit_room_update(room)


@sio.event
async def start_game_event(sid, data):
    code = _sid_to_room.get(sid)
    room = game.get_room(code) if code else None
    if not room:
        return await _emit_error(sid, "You're not in a room.")

    try:
        question = game.start_game(room, sid)
    except game.GameError as e:
        return await _emit_error(sid, str(e))

    await _emit_room_update(room)
    sio.start_background_task(run_game, room)


@sio.event
async def submit_bluff_event(sid, data):
    code = _sid_to_room.get(sid)
    room = game.get_room(code) if code else None
    if not room:
        return await _emit_error(sid, "You're not in a room.")

    try:
        game.submit_bluff(room, sid, (data or {}).get("text", ""))
    except game.GameError as e:
        return await _emit_error(sid, str(e))

    await sio.emit(
        "writing_progress",
        {"submitted": len(room.bluffs), "total": len(room.alive())},
        room=room.code,
    )


@sio.event
async def submit_vote_event(sid, data):
    code = _sid_to_room.get(sid)
    room = game.get_room(code) if code else None
    if not room:
        return await _emit_error(sid, "You're not in a room.")

    try:
        game.submit_vote(room, sid, int((data or {}).get("option_index", -1)))
    except (game.GameError, TypeError, ValueError) as e:
        return await _emit_error(sid, str(e) if isinstance(e, game.GameError) else "Invalid vote.")

    await sio.emit(
        "voting_progress",
        {"submitted": len(room.votes), "total": len(room.alive())},
        room=room.code,
    )


# ── The game loop ────────────────────────────────────────────────────────────

async def run_game(room: game.Room) -> None:
    try:
        while True:
            await sio.emit(
                "round_started",
                {
                    "question": room.current_question["q"],
                    "round_num": room.round_num,
                    "total_rounds": room.total_rounds,
                    "write_seconds": game.WRITE_SECONDS,
                },
                room=room.code,
            )

            elapsed = 0
            while elapsed < game.WRITE_SECONDS and not game.all_bluffs_in(room):
                await sio.sleep(1)
                elapsed += 1

            options = game.start_voting(room)
            await sio.emit(
                "voting_started",
                {
                    "options": [o.text for o in options],
                    "vote_seconds": game.VOTE_SECONDS,
                },
                room=room.code,
            )

            elapsed = 0
            while elapsed < game.VOTE_SECONDS and not game.all_votes_in(room):
                await sio.sleep(1)
                elapsed += 1

            results = game.score_round(room)
            await sio.emit(
                "round_revealed",
                {**results, "players": _player_view(room)},
                room=room.code,
            )

            await sio.sleep(game.REVEAL_SECONDS)

            if game.is_game_over(room):
                ranked = game.end_game(room)
                await sio.emit(
                    "game_over",
                    {"rankings": [{"name": p.name, "score": p.score} for p in ranked]},
                    room=room.code,
                )
                break

            game.next_round(room)
    except Exception:
        logger.exception("Game loop crashed for room %s", room.code)
        await sio.emit("game_error", {"message": "The game hit an unexpected error."}, room=room.code)
