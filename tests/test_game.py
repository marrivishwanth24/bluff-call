"""Tests for the pure game-logic layer (game.py). No networking involved."""

import pytest

from app import game


@pytest.fixture(autouse=True)
def _clean_registry():
    """Each test gets an empty room registry."""
    game._rooms.clear()
    yield
    game._rooms.clear()


def make_room(n_players=3):
    room = game.create_room("host", "Host")
    for i in range(n_players - 1):
        game.join_room(room, f"p{i}", f"Player{i}")
    return room


# ── Room / lobby ─────────────────────────────────────────────────────────────

def test_create_room_generates_unique_code():
    room1 = game.create_room("a", "Alice")
    room2 = game.create_room("b", "Bob")
    assert room1.code != room2.code
    assert len(room1.code) == 5


def test_get_room_is_case_insensitive():
    room = game.create_room("a", "Alice")
    assert game.get_room(room.code.lower()) is room


def test_join_room_rejects_duplicate_name():
    room = game.create_room("a", "Alice")
    with pytest.raises(game.GameError):
        game.join_room(room, "b", "alice")  # case-insensitive clash


def test_join_room_rejects_after_game_started():
    room = make_room(3)
    game.start_game(room, "host")
    with pytest.raises(game.GameError):
        game.join_room(room, "late", "Latecomer")


def test_join_room_rejects_when_full():
    room = game.create_room("host", "Host")
    for i in range(game.MAX_PLAYERS - 1):
        game.join_room(room, f"p{i}", f"P{i}")
    with pytest.raises(game.GameError):
        game.join_room(room, "overflow", "Overflow")


# ── Starting the game ─────────────────────────────────────────────────────────

def test_start_game_requires_host():
    room = make_room(3)
    with pytest.raises(game.GameError):
        game.start_game(room, "p0")


def test_start_game_requires_minimum_players():
    room = make_room(2)
    with pytest.raises(game.GameError):
        game.start_game(room, "host")


def test_start_game_succeeds_and_enters_writing():
    room = make_room(3)
    question = game.start_game(room, "host")
    assert room.status == "writing"
    assert room.round_num == 1
    assert "q" in question and "a" in question


# ── Writing phase ─────────────────────────────────────────────────────────────

def test_submit_bluff_rejected_outside_writing_phase():
    room = make_room(3)
    with pytest.raises(game.GameError):
        game.submit_bluff(room, "host", "my bluff")


def test_submit_bluff_rejects_empty_text():
    room = make_room(3)
    game.start_game(room, "host")
    with pytest.raises(game.GameError):
        game.submit_bluff(room, "host", "   ")


def test_all_bluffs_in_tracks_alive_players_only():
    room = make_room(3)
    game.start_game(room, "host")
    assert not game.all_bluffs_in(room)
    game.submit_bluff(room, "host", "a")
    game.submit_bluff(room, "p0", "b")
    assert not game.all_bluffs_in(room)
    game.submit_bluff(room, "p1", "c")
    assert game.all_bluffs_in(room)


def test_disconnected_player_excluded_from_all_bluffs_in():
    room = make_room(3)
    game.start_game(room, "host")
    game.mark_disconnected(room, "p1")
    game.submit_bluff(room, "host", "a")
    game.submit_bluff(room, "p0", "b")
    assert game.all_bluffs_in(room)  # p1 disconnected, doesn't block


# ── Voting phase ──────────────────────────────────────────────────────────────

def test_start_voting_includes_real_answer_and_all_bluffs():
    room = make_room(3)
    question = game.start_game(room, "host")
    game.submit_bluff(room, "host", "bluff1")
    game.submit_bluff(room, "p0", "bluff2")
    options = game.start_voting(room)

    assert room.status == "voting"
    texts = {o.text for o in options}
    assert question["a"] in texts
    assert "bluff1" in texts and "bluff2" in texts
    assert sum(o.is_real for o in options) == 1


def test_cannot_vote_for_own_bluff():
    room = make_room(3)
    game.start_game(room, "host")
    game.submit_bluff(room, "host", "my own bluff")
    game.submit_bluff(room, "p0", "other bluff")
    game.start_voting(room)

    own_index = next(i for i, o in enumerate(room.answer_options) if o.author_sid == "host")
    with pytest.raises(game.GameError):
        game.submit_vote(room, "host", own_index)


def test_vote_outside_voting_phase_rejected():
    room = make_room(3)
    game.start_game(room, "host")  # still 'writing'
    with pytest.raises(game.GameError):
        game.submit_vote(room, "host", 0)


# ── Scoring ───────────────────────────────────────────────────────────────────

def test_scoring_awards_points_for_correct_guess():
    room = make_room(3)
    question = game.start_game(room, "host")
    game.submit_bluff(room, "host", "bluff1")
    game.submit_bluff(room, "p0", "bluff2")
    game.start_voting(room)

    real_index = next(i for i, o in enumerate(room.answer_options) if o.is_real)
    game.submit_vote(room, "p1", real_index)  # p1 didn't bluff (no bluff submitted), votes correctly

    results = game.score_round(room)

    assert room.players["p1"].score == game.CORRECT_GUESS_POINTS
    assert results["real_answer"] == question["a"]
    assert "p1" in results["correct_voters"] or room.players["p1"].name in results["correct_voters"]


def test_scoring_awards_points_per_player_fooled():
    room = make_room(3)
    game.start_game(room, "host")
    game.submit_bluff(room, "host", "convincing bluff")
    game.submit_bluff(room, "p0", "other bluff")
    game.start_voting(room)

    host_bluff_index = next(i for i, o in enumerate(room.answer_options) if o.author_sid == "host")
    game.submit_vote(room, "p0", host_bluff_index)
    game.submit_vote(room, "p1", host_bluff_index)

    game.score_round(room)

    assert room.players["host"].score == game.FOOLED_VOTE_POINTS * 2


def test_scoring_handles_nobody_voting():
    room = make_room(3)
    game.start_game(room, "host")
    game.submit_bluff(room, "host", "a")
    game.start_voting(room)

    results = game.score_round(room)  # no votes cast at all

    assert all(p.score == 0 for p in room.players.values())
    assert results["correct_voters"] == []


# ── Round / game progression ──────────────────────────────────────────────────

def test_next_round_does_not_repeat_question_until_bank_exhausted():
    room = make_room(3)
    seen = set()
    for _ in range(len(__import__("app.questions", fromlist=["QUESTIONS"]).QUESTIONS)):
        q = game.next_round(room)
        assert q["q"] not in seen
        seen.add(q["q"])


def test_is_game_over_after_total_rounds():
    room = make_room(3)
    room.total_rounds = 2
    game.start_game(room, "host")  # round 1
    assert not game.is_game_over(room)
    game.next_round(room)  # round 2
    assert game.is_game_over(room)


def test_end_game_ranks_players_by_score_descending():
    room = make_room(3)
    room.players["host"].score = 500
    room.players["p0"].score = 1500
    room.players["p1"].score = 1000

    ranked = game.end_game(room)

    assert [p.sid for p in ranked] == ["p0", "p1", "host"]
    assert room.status == "game_over"


# ── Snapshot (client-safe view) ────────────────────────────────────────────────

def test_room_snapshot_does_not_leak_answers():
    room = make_room(3)
    game.start_game(room, "host")
    snapshot = game.room_snapshot(room)

    assert "current_question" not in str(snapshot.keys())
    assert "answer_options" not in snapshot
    player_names = {p["name"] for p in snapshot["players"]}
    assert player_names == {"Host", "Player0", "Player1"}
