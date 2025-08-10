"""
Simple real‑time chat server for the EspressoLabs coding challenge.

This server uses Python's built‑in ``asyncio`` and the
``websockets`` library (already available in this environment) to
handle WebSocket connections.  It also spins up a lightweight HTTP
server to serve static files (HTML, CSS and JavaScript) from the
``client`` directory.

The protocol between client and server uses JSON messages with
different ``type`` fields.  The following message types are
understood:

 * ``join`` – sent by the client when a user picks a username and
   room to join.  Example: ``{"type": "join", "username": "Alice",
   "room": "general"}``.
 * ``message`` – a chat message sent by a user.  Example:
   ``{"type": "message", "room": "general", "username": "Alice",
   "text": "Hello world"}``.
 * ``switch_room`` – optional type allowing a user to switch rooms
   without disconnecting.  The client sends
   ``{"type": "switch_room", "room": "newroom", "username": "Alice"}``.

On join the server responds with an ``init`` event containing the
current room, list of all rooms, existing messages and list of
connected users.  When new messages arrive they are broadcast to
everyone in the appropriate room using a ``message`` event.
System messages (users joining/leaving) use a ``system`` event and
have a ``message`` field.  Whenever the list of users in a room
changes the server broadcasts a ``users`` event.
"""

import asyncio
import json
import logging
import pathlib
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from typing import Dict, List, Any, Set

import websockets

# Configure basic logging for debugging.  This can be helpful when
# developing locally.  In production environments you would likely
# integrate with a more sophisticated logging solution.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Directory containing the static client files (index.html,
# app.js, style.css).  The HTTP server will serve files from this
# directory.
CLIENT_DIR = pathlib.Path(__file__).resolve().parent / "client"

# ``rooms`` is a mapping from room name to a dictionary containing
# connected websockets (as keys) with their usernames as values, and
# a list of message objects (each containing ``username`` and ``text``)
# representing the chat history for that room.  Everything is kept in
# memory since persistence is not required for this challenge.
rooms: Dict[str, Dict[str, Any]] = {}

# ``user_rooms`` maps each websocket connection to the name of the
# room it has joined.  When a user disconnects, the mapping allows
# us to remove them cleanly from the appropriate room.
user_rooms: Dict[websockets.WebSocketServerProtocol, str] = {}

# A set containing all active websockets regardless of room.  This
# allows us to broadcast events (like new room creation) to everyone
# connected.
all_websockets: Set[websockets.WebSocketServerProtocol] = set()


async def broadcast_to_room(room: str, message: Dict[str, Any]) -> None:
    """Send a JSON message to all websockets connected to the given room.

    If a websocket connection fails during sending (e.g. because
    the client disconnected), it is removed from the room and the
    ``user_rooms`` mapping.

    Args:
        room: Name of the room to broadcast the message to.
        message: A JSON‑serialisable dictionary representing the
            message to send.
    """
    if room not in rooms:
        return
    websockets_to_remove: List[websockets.WebSocketServerProtocol] = []
    for ws in list(rooms[room]["users"].keys()):
        try:
            await ws.send(json.dumps(message))
        except Exception:
            # Mark connection for removal if sending fails
            websockets_to_remove.append(ws)
    for ws in websockets_to_remove:
        username = rooms[room]["users"].pop(ws, None)
        user_rooms.pop(ws, None)
        all_websockets.discard(ws)
        if username:
            await broadcast_to_room(room, {
                "type": "system",
                "message": f"{username} disconnected unexpectedly."
            })
        await broadcast_user_list(room)


async def broadcast_user_list(room: str) -> None:
    """Send the updated list of usernames in a room to everyone there."""
    if room not in rooms:
        return
    users = list(rooms[room]["users"].values())
    await broadcast_to_room(room, {
        "type": "users",
        "users": users
    })


async def broadcast_rooms_list() -> None:
    """Send the list of available rooms to all connected users."""
    room_names = list(rooms.keys())
    for ws in list(all_websockets):
        try:
            await ws.send(json.dumps({"type": "rooms", "rooms": room_names}))
        except Exception:
            all_websockets.discard(ws)


async def handle_join(ws: websockets.WebSocketServerProtocol, data: Dict[str, Any]) -> None:
    """Handle a ``join`` request from a client.

    This registers the user in the requested room, creates the room
    if it does not already exist, and sends back initial state
    including existing messages and user list.  It also broadcasts
    system messages and updates to other users in the room and
    notifies everyone about new rooms.
    """
    username = data.get("username", "Anonymous")
    room = data.get("room", "default")
    # Ensure the room exists
    if room not in rooms:
        rooms[room] = {"users": {}, "messages": []}
        # Since this is a new room, notify everyone
        await broadcast_rooms_list()
    # If the websocket was already in another room remove it there
    previous_room = user_rooms.get(ws)
    if previous_room and previous_room != room:
        # Remove from old room and notify others
        old_username = rooms[previous_room]["users"].pop(ws, None)
        await broadcast_to_room(previous_room, {
            "type": "system",
            "message": f"{old_username} has left the room."
        })
        await broadcast_user_list(previous_room)
    # Register user in new room
    rooms[room]["users"][ws] = username
    user_rooms[ws] = room
    all_websockets.add(ws)
    # Send initialization data: existing messages, users and available rooms
    await ws.send(json.dumps({
        "type": "init",
        "room": room,
        "messages": rooms[room]["messages"],
        "users": list(rooms[room]["users"].values()),
        "rooms": list(rooms.keys())
    }))
    # Notify others in the room that a user joined
    await broadcast_to_room(room, {
        "type": "system",
        "message": f"{username} has joined the room."
    })
    await broadcast_user_list(room)


async def handle_message(ws: websockets.WebSocketServerProtocol, data: Dict[str, Any]) -> None:
    """Handle a ``message`` event from a client by broadcasting it."""
    room = data.get("room")
    username = data.get("username")
    text = data.get("text", "")
    if not room or room not in rooms or not username or not text:
        return
    msg = {"username": username, "text": text}
    rooms[room]["messages"].append(msg)
    # Keep only the latest 100 messages to prevent unbounded memory use
    if len(rooms[room]["messages"]) > 100:
        rooms[room]["messages"] = rooms[room]["messages"][-100:]
    await broadcast_to_room(room, {
        "type": "message",
        "message": msg
    })


async def ws_handler(ws: websockets.WebSocketServerProtocol) -> None:
    """Main WebSocket connection handler.

    This coroutine listens for incoming JSON messages from the client
    and dispatches them to the appropriate handler.  It also takes
    care of cleaning up the user on disconnect.
    """
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logging.warning("Received non‑JSON data: %s", raw)
                continue
            mtype = data.get("type")
            if mtype == "join":
                await handle_join(ws, data)
            elif mtype == "message":
                await handle_message(ws, data)
            elif mtype == "switch_room":
                # ``switch_room`` behaves like ``join`` for simplicity
                await handle_join(ws, data)
    except websockets.ConnectionClosed:
        pass
    finally:
        # Clean up on disconnect
        room = user_rooms.pop(ws, None)
        username = None
        if room and room in rooms and ws in rooms[room]["users"]:
            username = rooms[room]["users"].pop(ws)
        all_websockets.discard(ws)
        if room and username:
            await broadcast_to_room(room, {
                "type": "system",
                "message": f"{username} has left the room."
            })
            await broadcast_user_list(room)


def start_http_server(port: int = 8000) -> None:
    """Start a simple HTTP server serving files from CLIENT_DIR.

    The HTTP server runs in its own thread so as not to block the
    asyncio event loop that runs the WebSocket server.
    """
    handler_class = type(
        "CustomHandler",
        (SimpleHTTPRequestHandler,),
        {"directory": str(CLIENT_DIR)}
    )
    with TCPServer(("", port), handler_class) as httpd:
        logging.info("HTTP server serving %s on port %d", CLIENT_DIR, port)
        httpd.serve_forever()


async def main() -> None:
    """Entry point that launches both HTTP and WebSocket servers."""
    # Start the HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server, args=(8000,), daemon=True)
    http_thread.start()
    # Start the WebSocket server
    ws_server = await websockets.serve(ws_handler, "", 6789)
    logging.info("WebSocket server started on port 6789")
    # Run forever
    await ws_server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server shutting down")