# Bluff Call

A real-time multiplayer bluffing game about programming trivia. Create a
room, share the code, and up to 10 players join from any phone or laptop —
no login, no install. Everyone's screen stays in sync live.

**How to play:** Each round, everyone sees a real (and surprising) question
about how some language or API actually behaves. Every player writes their
own convincing fake answer. All the answers — the real one and everyone's
bluffs — get shown anonymously, and everyone votes for the one they think
is true. Score points for finding the real answer, *more* points for every
person you fool into picking yours. After 8 rounds, highest score wins.

## Why this game, not a generic party game clone

Most quick multiplayer demos are the same "trivia" or "drawing" clone. This
one is themed around real, verified language/API quirks (`[] + []` in
JavaScript, `NULL = NULL` in SQL, `round(2.5)` in Python) — which makes the
bluffing genuinely interesting: a good fake answer has to actually *sound*
like something that language would do. It's a classic Fibbage/Balderdash
format applied to something a technical audience finds funny, not generic.

## Architecture

```
Browser (any device)
      │  Socket.io (WebSocket, falls back to polling)
      ▼
FastAPI + python-socketio, single ASGI app
      │
      ├── One asyncio background task per room, started when the host
      │   clicks "start" — drives every round sequentially:
      │
      │     writing (45s or all submitted)
      │        │
      │        ▼
      │     voting (30s or all voted)
      │        │
      │        ▼
      │     reveal + scoring (8s pause)
      │        │
      │        ▼
      │     next round, or game_over
      │
      └── In-memory room registry (dict: code -> Room)
```

## Key design decisions

**One coroutine per room owns every phase transition.** Client events
(`submit_bluff_event`, `submit_vote_event`) only ever write into
`room.bluffs` / `room.votes` — they never advance `room.status` themselves.
The room's single background task is the only thing that reads those dicts
and decides to move the game forward. That rules out an entire class of
races (two different code paths both trying to advance the same round) by
construction, not by locking.

**The server never sends players information they shouldn't have.**
`room_snapshot()` never includes the current question's answer or who wrote
which bluff. During voting, clients only ever receive the shuffled, author-
stripped option text — the real answer and authorship are revealed only in
`round_revealed`, after voting has closed. `tests/test_game.py` asserts
this directly rather than trusting it by inspection.

**In-memory state, not a database.** A live game session has nothing worth
persisting once it ends — unlike a project with durable records, there's no
reason to pay for a DB here. The trade-off is explicit: state doesn't
survive a server restart or span multiple instances. Fine for this game's
actual usage pattern (one short, live, in-the-same-call session); the fix
if that ever mattered would be Redis-backed room state, not Postgres.

**`python-socketio` over raw WebSockets.** Rooms, broadcast-to-room, and
reconnect/transport-fallback handling are exactly what Socket.io is for —
hand-rolling that on top of FastAPI's raw WebSocket support would mean
re-implementing a chunk of what this library already does correctly.

## Project Structure

```
bluff-call/
├── app/
│   ├── main.py       ← Mounts FastAPI (dashboard, /health) + Socket.io into one ASGI app
│   ├── events.py       ← Socket.io handlers + the per-room game loop
│   ├── game.py           ← Pure game state machine (rooms, rounds, scoring) — no networking
│   └── questions.py        ← Curated, fact-checked question bank (40 entries)
├── static/
│   └── index.html    ← Single-page client: join/lobby/writing/voting/reveal/game-over screens
├── tests/
│   ├── test_game.py        ← Pure logic tests (22) — no server needed
│   ├── test_events.py        ← Real Socket.io clients against a real server (4)
│   └── test_full_game.py       ← Plays an entire game to completion over real connections (1)
├── requirements.txt
├── railway.json / Procfile
```

## Getting Started

```bash
git clone https://github.com/marrivishwanth24/bluff-call
cd bluff-call
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`, create a room, open it again in two more tabs
(or send the room code to friends) to play.

## Running Tests

```bash
pip install -r requirements.txt
pytest
```

27 tests. The game-logic tests (`test_game.py`) need no server or network
at all. The integration tests (`test_events.py`, `test_full_game.py`) spin
up a real server and drive it with real Socket.io clients — including
playing a complete 3-round game start to finish — rather than mocking the
transport layer, since the thing most likely to have a subtle bug here is
the wiring between the game loop and the event handlers, which a pure
logic test can't see.

## Author

**Vishwanth Marri**
- GitHub: [github.com/marrivishwanth24](https://github.com/marrivishwanth24)
