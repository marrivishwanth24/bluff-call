"""Integration test: a real server, real Socket.io clients, a full round
played end to end. This is the test that actually proves the networking
layer and the game loop agree with each other -- the pure game.py tests
can't catch a wiring bug between events.py and the loop.
"""

import asyncio

import pytest
import socketio
import uvicorn

from app import game
from app.main import app as asgi_app


@pytest.fixture(autouse=True)
def _clean_registry():
    game._rooms.clear()
    yield
    game._rooms.clear()


@pytest.fixture
async def server():
    config = uvicorn.Config(asgi_app, host="127.0.0.1", port=8765, log_level="warning")
    srv = uvicorn.Server(config)
    task = asyncio.create_task(srv.serve())
    await asyncio.sleep(0.5)
    yield "http://127.0.0.1:8765"
    srv.should_exit = True
    await task


async def _connect() -> socketio.AsyncSimpleClient:
    client = socketio.AsyncSimpleClient()
    await client.connect("http://127.0.0.1:8765", socketio_path="/socket.io")
    return client


async def _drain_until(client, event_name, timeout=10):
    """Receive events until one with the given name shows up (skip others)."""
    async with asyncio.timeout(timeout):
        while True:
            name, data = await client.receive()
            if name == event_name:
                return data


@pytest.mark.asyncio
async def test_full_round_three_players(server, monkeypatch):
    monkeypatch.setattr(game, "MIN_PLAYERS", 3)

    host = await _connect()
    p1 = await _connect()
    p2 = await _connect()

    await host.emit("create_room", {"name": "Host"})
    room_data = await _drain_until(host, "room_created")
    code = room_data["code"]

    await p1.emit("join_room_event", {"code": code, "name": "P1"})
    await _drain_until(p1, "room_joined")
    await p2.emit("join_room_event", {"code": code, "name": "P2"})
    await _drain_until(p2, "room_joined")

    await host.emit("start_game_event", {})
    round_data = await _drain_until(host, "round_started")
    assert round_data["round_num"] == 1
    assert "question" in round_data

    # All three submit bluffs
    await host.emit("submit_bluff_event", {"text": "host bluff"})
    await p1.emit("submit_bluff_event", {"text": "p1 bluff"})
    await p2.emit("submit_bluff_event", {"text": "p2 bluff"})

    voting_data = await _drain_until(host, "voting_started")
    options = voting_data["options"]
    # 1 real answer + 3 player bluffs (host, p1, p2 all submitted) = 4 options
    assert len(options) == 4

    # Options are shuffled and anonymized -- vote for any option that isn't
    # the text this client itself submitted (the server rejects self-votes,
    # same as a real UI would just disable that option).
    def _safe_index(own_text):
        return next(i for i, text in enumerate(options) if text != own_text)

    await host.emit("submit_vote_event", {"option_index": _safe_index("host bluff")})
    await p1.emit("submit_vote_event", {"option_index": _safe_index("p1 bluff")})
    await p2.emit("submit_vote_event", {"option_index": _safe_index("p2 bluff")})

    reveal_data = await _drain_until(host, "round_revealed")
    assert reveal_data["question"] == round_data["question"]
    assert len(reveal_data["options"]) == 4
    assert len(reveal_data["players"]) == 3

    await host.disconnect()
    await p1.disconnect()
    await p2.disconnect()


@pytest.mark.asyncio
async def test_join_rejects_duplicate_name_over_the_wire(server):
    host = await _connect()
    dup = await _connect()

    await host.emit("create_room", {"name": "Alice"})
    room_data = await _drain_until(host, "room_created")

    await dup.emit("join_room_event", {"code": room_data["code"], "name": "Alice"})
    err = await _drain_until(dup, "game_error")
    assert "taken" in err["message"].lower()

    await host.disconnect()
    await dup.disconnect()


@pytest.mark.asyncio
async def test_start_game_rejects_non_host(server):
    host = await _connect()
    p1 = await _connect()
    p2 = await _connect()

    await host.emit("create_room", {"name": "Host"})
    room_data = await _drain_until(host, "room_created")
    await p1.emit("join_room_event", {"code": room_data["code"], "name": "P1"})
    await _drain_until(p1, "room_joined")
    await p2.emit("join_room_event", {"code": room_data["code"], "name": "P2"})
    await _drain_until(p2, "room_joined")

    await p1.emit("start_game_event", {})
    err = await _drain_until(p1, "game_error")
    assert "host" in err["message"].lower()

    await host.disconnect()
    await p1.disconnect()
    await p2.disconnect()


@pytest.mark.asyncio
async def test_disconnect_marks_player_and_broadcasts_update(server):
    host = await _connect()
    p1 = await _connect()

    await host.emit("create_room", {"name": "Host"})
    room_data = await _drain_until(host, "room_created")
    await p1.emit("join_room_event", {"code": room_data["code"], "name": "P1"})
    await _drain_until(p1, "room_joined")
    await _drain_until(host, "room_update")  # the broadcast from P1's join -- not the one we're testing

    await p1.disconnect()
    update = await _drain_until(host, "room_update", timeout=5)
    p1_entry = next(p for p in update["players"] if p["name"] == "P1")
    assert p1_entry["connected"] is False

    await host.disconnect()
