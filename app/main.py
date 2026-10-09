"""
main.py — mounts the FastAPI app (static dashboard + /health) together with
the Socket.io ASGI app (real-time game events) into a single ASGI app, which
is what actually gets served.
"""

import socketio
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.events import sio

fastapi_app = FastAPI(title="Bluff Call")
fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")


@fastapi_app.get("/")
async def index():
    return FileResponse("static/index.html")


@fastapi_app.get("/health")
async def health():
    return {"status": "healthy"}


# socketio.ASGIApp wraps the FastAPI app, routing /socket.io/* to Socket.io
# and everything else through to FastAPI. This combined object is the real
# ASGI entry point (see Procfile / railway.json: `app.main:app`).
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
