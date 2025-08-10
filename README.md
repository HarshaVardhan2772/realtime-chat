# Real‑Time Chat App for EspressoLabs Coding Challenge

This repository contains a simple real‑time chat application created as
part of the EspressoLabs coding challenge described in their August 1,
2025 blog post【264466484445473†L131-L183】.  The challenge asked candidates
to build a chat system where authenticated users can create and join
multiple chat rooms and exchange messages via WebSockets.  Although
the original specification suggested using React + TypeScript on the
frontend and Node.js + Express + Socket.IO on the backend, the
environment provided for this solution does not allow the
installation of additional NPM packages.  To work within those
constraints the chat server is implemented in Python using
[`asyncio`](https://docs.python.org/3/library/asyncio.html) and the
[`websockets`](https://websockets.readthedocs.io/) library (already
available in this environment) while the frontend is a lightweight
HTML/CSS/JavaScript application.  Despite these implementation
details, the app satisfies the core requirements of the challenge:

* **Real‑time communication.**  Clients communicate with the server
  using the WebSocket protocol.  Messages are broadcast to all users
  within a chat room in real time【264466484445473†L131-L143】.
* **Multiple chat rooms.**  Users can create new rooms or join
  existing ones.  The server maintains isolated chat histories and
  user lists for each room【264466484445473†L150-L155】.
* **User management.**  On joining or leaving, the server informs
  other members of the room via system messages and updates the list
  of online users.  The server keeps a bounded history (latest 100
  messages) per room to prevent unbounded memory growth.

Please note that because external OAuth services (Google/MS) cannot
be configured in this sandbox, the app uses a simple username entry
for authentication.  The code is structured so that real OAuth
providers could be integrated in the future by replacing the login
screen with appropriate flows.

## Getting started

### Prerequisites

* Python 3.8+ (the project was developed with Python 3.11).
* The `websockets` package (version 10.3 is bundled in this
  environment).  No additional installations are required.

### Running the server

To start the chat server and the accompanying static HTTP server, run
the following commands from the `realtime-chat` directory:

```bash
cd realtime-chat
python3 server.py
```

Two services will start:

* **HTTP server on port 8000** – serves the frontend files from
  `client/index.html`.  Navigate to `http://localhost:8000` in your
  browser to load the application.  If the provided environment
  blocks `localhost`, consider hosting the `client` directory on
  another development machine or serving it via GitHub Pages.
* **WebSocket server on port 6789** – handles real‑time chat.

If you wish to change the ports, edit the corresponding values in
`server.py` (see the definitions of `start_http_server()` and
`websockets.serve()`).

### Using the app

1. Open the application in your browser (`http://localhost:8000`).
2. Enter a display name and a room name, then click **Join**.
3. The chat interface appears.  You can:
   * Send messages to others in the same room.
   * See the list of rooms on the left and click on them to switch
     rooms.  New rooms can be created via the input and **Create**
     button.
   * View the list of users currently in your room.

Each message shows the sender’s name and content.  System events
such as users joining/leaving are displayed in italic for clarity.

### Architecture overview

The project is deliberately small to fit within the 90‑minute time
window advised by EspressoLabs【264466484445473†L131-L183】.  The key
components are:

| Component      | File/technology                 | Responsibilities                               |
|---------------|----------------------------------|-----------------------------------------------|
| **HTTP server** | `server.py` (Python `http.server`) | Serves static assets (HTML, CSS, JS) to the browser. |
| **WebSocket server** | `server.py` (Python `websockets`) | Manages rooms, user lists and message broadcasting. |
| **Client UI** | `client/index.html`, `client/style.css` | Renders the login form, chat layout and style. |
| **Client logic** | `client/app.js`                    | Connects to the WebSocket server, sends/receives messages and updates the DOM accordingly. |

Each WebSocket client sends and receives JSON messages with a
``type`` field indicating the action (e.g. ``join``, ``message``,
``rooms``).  The server keeps a dictionary of rooms, where each room
contains a set of connected sockets, a mapping of sockets to
usernames, and an in‑memory message history.  When a user joins a
room the server emits an `init` event containing the room’s current
state.  Additional events keep clients synchronised as users come and
go.

## Improvements with more time

If more time and fewer environmental restrictions were available, I
would explore the following enhancements:

* **OAuth authentication.**  Integrate Google or Microsoft login so
  that users authenticate with their real email and avatar
  information as specified in the challenge【264466484445473†L144-L148】.
* **Persistent storage.**  Use a database (e.g. PostgreSQL or
  MongoDB) to persist room metadata and message history.  That would
  allow chat history to survive server restarts and enable features
  like message search【264466484445473†L163-L165】.
* **Front‑end framework.**  Port the current vanilla JS UI to
  React + TypeScript, perhaps using Vite or Next.js for build tooling
  once NPM package installation is allowed.  A component‑based
  approach would simplify state management and allow reuse.
* **Testing.**  Add unit tests (e.g. via `pytest` or Jest) for
  message handling and integration tests for the WebSocket protocol
  to catch regressions【264466484445473†L161-L164】.
* **Deployment.**  Containerise the application with Docker and add
  configuration for cloud deployment (e.g. on Railway or Heroku) to
  demonstrate scalability and fault tolerance【264466484445473†L175-L182】.

## Demo video

A short demo video is typically required as part of this challenge
【264466484445473†L168-L174】.  To record your own walkthrough:

1. Start the server locally and open the app in a browser.
2. Use screen recording software (e.g. OBS Studio, QuickTime or
   Screencastify) to capture yourself creating rooms, sending
   messages and switching between rooms.
3. Save the video file and include its link in your GitHub
   repository’s README.

## Conclusion

This project delivers a functional real‑time chat application under
tight time and tooling constraints.  It demonstrates the ability to
design, implement and document a web application featuring
WebSocket‑based communication, dynamic room management and a clean UI
within the allotted timeframe.