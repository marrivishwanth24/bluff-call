"""Plays an entire game to completion (all rounds -> game_over) over real
Socket.io connections. The single-round test proves one round's wiring is
correct; this proves the loop actually terminates and a winner is produced
rather than hanging or crashing on the round->round transition.
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
    config = uvicorn.Config(asgi_app, host="127.0.0.1", port=8766, log_level="warning")
    srv = uvicorn.Server(config)
    task = asyncio.create_task(srv.serve())
    await asyncio.sleep(0.5)
    yield "http://127.0.0.1:8766"
    srv.should_exit = True
    await task


async def _connect():
    client = socketio.AsyncSimpleClient()
    await client.connect("http://127.0.0.1:8766", socketio_path="/socket.io")
    return client


async def _drain_until(client, event_name, timeout=10):
    async with asyncio.timeout(timeout):
        while True:
            name, data = await client.receive()
            if name == event_name:
                return data


@pytest.mark.asyncio
async def test_full_game_three_players_reaches_game_over(server, monkeypatch):
    monkeypatch.setattr(game, "MIN_PLAYERS", 3)

    host, p1, p2 = await _connect(), await _connect(), await _connect()
    clients = {"host": host, "p1": p1, "p2": p2}
    names = {"host": "host bluff", "p1": "p1 bluff", "p2": "p2 bluff"}

    await host.emit("create_room", {"name": "Host"})
    room_data = await _drain_until(host, "room_created")
    code = room_data["code"]
    # TOTAL_ROUNDS is a dataclass field default bound at import time, not a
    # live reference -- monkeypatching the module constant after Room exists
    # wouldn't reach it. Setting it on the actual instance does, since this
    # test runs in-process with the server and shares its module state.
    game._rooms[code].total_rounds = 3

    for key, client in (("p1", p1), ("p2", p2)):
        await client.emit("join_room_event", {"code": code, "name": key.upper()})
        await _drain_until(client, "room_joined")

    await host.emit("start_game_event", {})

    rounds_seen = 0
    while True:
        round_data = await _drain_until(host, "round_started")
        rounds_seen += 1

        for key, client in clients.items():
            await client.emit("submit_bluff_event", {"text": names[key]})

        voting_data = await _drain_until(host, "voting_started")
        options = voting_data["options"]
        assert len(options) == 4  # 3 bluffs + 1 real answer, every round

        for key, client in clients.items():
            idx = next(i for i, t in enumerate(options) if t != names[key])
            await client.emit("submit_vote_event", {"option_index": idx})

        await _drain_until(host, "round_revealed")

        if rounds_seen >= 3:
            game_over = await _drain_until(host, "game_over", timeout=15)
            break

    assert len(game_over["rankings"]) == 3
    assert {r["name"] for r in game_over["rankings"]} == {"Host", "P1", "P2"}
    # Rankings must actually be sorted descending by score
    scores = [r["score"] for r in game_over["rankings"]]
    assert scores == sorted(scores, reverse=True)

    for c in clients.values():
        await c.disconnect()
