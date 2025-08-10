// Client‑side logic for the real‑time chat app.
//
// This script handles the UI transitions between the login form and
// the chat interface, establishes a WebSocket connection to the
// server, and manages sending and receiving messages in JSON
// format.  See ``server.py`` for details of the protocol.

(function () {
  // Obtain references to DOM elements
  const loginDiv = document.getElementById("login");
  const chatDiv = document.getElementById("chat");
  const joinBtn = document.getElementById("joinBtn");
  const usernameInput = document.getElementById("username");
  const roomInput = document.getElementById("room");
  const roomsList = document.getElementById("roomsList");
  const usersList = document.getElementById("usersList");
  const newRoomName = document.getElementById("newRoomName");
  const createRoomBtn = document.getElementById("createRoomBtn");
  const messagesDiv = document.getElementById("messages");
  const messageForm = document.getElementById("messageForm");
  const messageInput = document.getElementById("messageInput");

  // State variables
  let ws;
  let username = "";
  let currentRoom = "";

  // Determine websocket server host based on current location.
  // If served from http://localhost:8000, we expect the WS server on
  // ws://localhost:6789.  Using location.hostname ensures the
  // hostname matches even when accessed via IP.
  const wsUrl = `ws://${location.hostname}:6789`;

  function connectWebSocket() {
    ws = new WebSocket(wsUrl);
    ws.addEventListener("open", () => {
      console.log("WebSocket connected");
    });
    ws.addEventListener("message", (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (e) {
        console.warn("Non‑JSON message", event.data);
        return;
      }
      handleServerEvent(data);
    });
    ws.addEventListener("close", () => {
      console.warn("WebSocket disconnected. Attempting reconnect in 1s...");
      setTimeout(connectWebSocket, 1000);
    });
  }

  connectWebSocket();

  // Handle click on the "Join" button
  joinBtn.addEventListener("click", () => {
    const nameVal = usernameInput.value.trim();
    const roomVal = roomInput.value.trim() || "general";
    if (!nameVal) {
      alert("Please enter your name.");
      return;
    }
    username = nameVal;
    currentRoom = roomVal;
    sendJson({ type: "join", username, room: currentRoom });
  });

  // Handle creation of a new room
  createRoomBtn.addEventListener("click", () => {
    const roomVal = newRoomName.value.trim();
    if (!roomVal) return;
    currentRoom = roomVal;
    sendJson({ type: "join", username, room: currentRoom });
    newRoomName.value = "";
  });

  // Handle sending of chat messages
  messageForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;
    sendJson({ type: "message", room: currentRoom, username, text });
    messageInput.value = "";
  });

  // Send a JSON message over the WebSocket if it's open
  function sendJson(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  }

  // Handle incoming events from the server
  function handleServerEvent(data) {
    switch (data.type) {
      case "init":
        onInit(data);
        break;
      case "rooms":
        updateRooms(data.rooms);
        break;
      case "users":
        updateUsers(data.users);
        break;
      case "message":
        addChatMessage(data.message.username, data.message.text);
        break;
      case "system":
        addSystemMessage(data.message);
        break;
      default:
        console.warn("Unknown event", data);
    }
  }

  // Called when the server responds to a join/switch request
  function onInit(data) {
    // Hide login and show chat UI
    loginDiv.classList.add("hidden");
    chatDiv.classList.remove("hidden");
    currentRoom = data.room;
    // Update rooms and users
    updateRooms(data.rooms);
    updateUsers(data.users);
    // Clear any existing messages
    messagesDiv.innerHTML = "";
    // Render history
    data.messages.forEach((msg) => {
      addChatMessage(msg.username, msg.text);
    });
  }

  // Render the list of available rooms in the sidebar
  function updateRooms(rooms) {
    roomsList.innerHTML = "";
    rooms.forEach((room) => {
      const li = document.createElement("li");
      li.textContent = room;
      if (room === currentRoom) {
        li.style.fontWeight = "bold";
      }
      li.addEventListener("click", () => {
        if (room !== currentRoom) {
          currentRoom = room;
          sendJson({ type: "join", username, room: currentRoom });
        }
      });
      roomsList.appendChild(li);
    });
  }

  // Render the list of users in the current room
  function updateUsers(users) {
    usersList.innerHTML = "";
    users.forEach((user) => {
      const li = document.createElement("li");
      li.textContent = user;
      usersList.appendChild(li);
    });
  }

  // Add a regular chat message to the message view
  function addChatMessage(user, text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message";
    const userSpan = document.createElement("span");
    userSpan.className = "user";
    userSpan.textContent = user + ":";
    const textSpan = document.createElement("span");
    textSpan.textContent = " " + text;
    msgDiv.appendChild(userSpan);
    msgDiv.appendChild(textSpan);
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // Add a system message (join/leave notifications) to the message view
  function addSystemMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message system";
    msgDiv.textContent = text;
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }
})();