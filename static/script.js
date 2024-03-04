const apiKey = WATCH_PARTY_API_KEY;
const userId = WATCH_PARTY_USER_ID;

const API_ENDPOINTS = {
  MESSAGES_URL: '/api/room/messages',
  SEND_MESSAGE_URL: '/api/message/post',
  USERNAME_UPDATE_URL: '/api/username/change',
  PASSWORD_UPDATE_URL: '/api/password/change',
  ROOM_NAME_UPDATE_URL: '/api/room/name/change'
};


// let recentMessageId = 0;

let max_id = 0;

let getAllChatsReq = {
  room_id: 0
};

let postRequest = {
  room_id: 0,
  body: ''
};

let updatePasswordRequest = {
  password: ''
};

/* For room.html */

// TODO: Fetch the list of existing chat messages.
// POST to the API when the user posts a new message.
// Automatically poll for new messages on a regular interval.
// Allow changing the name of a room
async function performRequest(url, data, method) {
  const headers = new Headers({
      'Api-Key': apiKey,
      'Content-Type': 'application/json',
      'User-Id': userId
  });


  const fetchOptions = {
      method: method,
      headers: headers,
  };

  if (method !== 'GET') fetchOptions.body = JSON.stringify(data);

  try {
      const response = await fetch(url, fetchOptions);
      return await response.json(); 
  } catch (error) {
      console.error('Request failed:', error);
      return null; 
  }
}

async function postMessage(roomId) {
  const postRequest = {
    room_id: roomId,
    body: document.querySelector('.comment_box textarea').value
  };

  const postResponse = await performRequest(API_ENDPOINTS.SEND_MESSAGE_URL, postRequest, 'POST');
  
  if (postResponse) {
    document.querySelector(".comment_box form").reset();
    getMessages(roomId);
  }
}

async function getMessages(roomId) {
  const fetchURL = `${API_ENDPOINTS.MESSAGES_URL}?room_id=${roomId}`;
  const messagesResponse = await performRequest(fetchURL, {}, 'GET');
  if (messagesResponse) {
    const messagesDiv = document.querySelector(".messages");
    messagesDiv.innerHTML = ''; 

    Object.keys(messagesResponse).forEach(msg => {
      const messageElement = document.createElement("message");
      let author = document.createElement("author");
      author.innerHTML = messagesResponse[msg].name;
      let content = document.createElement("content");
      content.innerHTML = messagesResponse[msg].body;
      messageElement.appendChild(author);
      messageElement.appendChild(content);
      messagesDiv.append(messageElement);
    });
  }
}


function startMessagePolling(roomId) {
  setInterval(() => getMessages(roomId),100);
}



async function updateRoomName(roomId, newName) {
  const response = await performRequest(API_ENDPOINTS.ROOM_NAME_UPDATE_URL, { room_id: roomId, name: newName }, 'POST');
  if (response) {
      document.querySelector('.roomName').textContent = newName;
      hideEditMode();
  } else {
      console.error('Failed to update the room name');
  }
}

function hideEditMode() {
  ['.display', '.edit'].forEach(selector => document.querySelector(selector).classList.toggle('hide'));
}

function updateDOM(selector, property, value) {
  document.querySelector(selector)[property] = value;
}



/* For profile.html */

// TODO: Allow updating the username and password

async function changeUsername(newUsername) {
  const response = await performRequest(API_ENDPOINTS.USERNAME_UPDATE_URL, { username: newUsername }, 'POST');
  if (response) {
      console.log("Successfully changed username to ", newUsername);
  } else {
      console.error('Failed to change username:', response?.error || 'Unknown error');
  }
}

async function changePassword(newPassword) {
  const response = await performRequest(API_ENDPOINTS.PASSWORD_UPDATE_URL, { password: newPassword}, 'POST');
  if (response) {
      console.log("Successfully changed password to ", newPassword);
  } else {
      console.error('Failed to change password:', response?.error || 'Unknown error');
  }
}
