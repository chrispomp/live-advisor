const micButton = document.getElementById('mic-button-container');
const endCallButton = document.getElementById('endCallButton');
const chatMessages = document.getElementById('chat-messages');
const audioIndicator = document.getElementById('audio-indicator');
let audioClient;
let isRecording = false;

micButton.addEventListener('click', () => {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

endCallButton.addEventListener('click', () => {
    if (isRecording) {
        stopRecording();
    }
    addMessage("Call ended. How else can I help you?", "assistant");
    if (audioClient) {
        audioClient.close();
    }
    initializeAudioClient();
});

async function initializeAudioClient() {
    // Create a new instance for a clean start
    audioClient = new AudioClient();

    let currentResponseText = '';
    let currentResponseElement = null;

    // Add event listeners instead of assigning callbacks
    audioClient.addEventListener('ready', () => {
        console.log('Audio client ready');
        updateConnectionStatus('Connected');
    });

    audioClient.addEventListener('connecting', () => {
        updateConnectionStatus('Connecting...');
    });

    audioClient.addEventListener('reconnecting', (event) => {
        updateConnectionStatus(`Reconnecting (Attempt ${event.detail})...`);
    });

    audioClient.addEventListener('disconnected', () => {
        updateConnectionStatus('Disconnected');
    });

    audioClient.addEventListener('reconnect_failed', () => {
        updateConnectionStatus('Reconnection Failed. Please refresh.');
        addMessage("I'm sorry, I was unable to reconnect. Please check your internet connection and refresh the page.", "assistant");
    });

    audioClient.addEventListener('session_id', (event) => {
        const sessionId = event.detail;
        const sessionIdText = document.getElementById('session-id-text');
        const sessionIdDisplay = document.getElementById('session-id-display');

        if (sessionIdText && sessionIdDisplay) {
            sessionIdText.textContent = `Session ID: ${sessionId}`;
            sessionIdDisplay.classList.remove('text-gray-400');
            sessionIdDisplay.classList.add('text-yellow-300');
        }
    });

    audioClient.addEventListener('audio', (event) => {
        audioIndicator.classList.remove('hidden');
    });

    audioClient.addEventListener('text', (event) => {
        const text = event.detail;
        if (text && text.trim()) {
            if (!currentResponseElement || !document.body.contains(currentResponseElement)) {
                currentResponseText = text;
                currentResponseElement = document.createElement('div');
                currentResponseElement.className = 'chat-message assistant-message';
                currentResponseElement.textContent = text;
                chatMessages.appendChild(currentResponseElement);
            } else {
                currentResponseText += ' ' + text.trim();
                currentResponseElement.textContent = currentResponseText;
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    });

    audioClient.addEventListener('turn_complete', () => {
        audioIndicator.classList.add('hidden');
        currentResponseText = '';
        currentResponseElement = null;
    });

    audioClient.addEventListener('error', (event) => {
        console.error('Audio client error:', event.detail);
        addMessage("Sorry, I encountered an error. Please try again.", "assistant");
        currentResponseText = '';
        currentResponseElement = null;
        updateConnectionStatus('Error');
    });

    audioClient.addEventListener('interrupted', () => {
        console.log('Interruption detected, stopping audio playback');
        audioIndicator.classList.add('hidden');
        audioClient.interrupt();
        currentResponseText = '';
        currentResponseElement = null;
    });

    // New event listener for user transcript
    audioClient.addEventListener('user_transcript', (event) => {
        const transcript = event.detail;
        const tempMessages = document.querySelectorAll('.user-message');
        if (tempMessages.length > 0) {
            const lastMessage = tempMessages[tempMessages.length - 1];
            lastMessage.textContent = transcript;
        }
    });

    try {
        await audioClient.connect();
    } catch (error) {
        console.error('Failed to initialize audio client:', error);
        updateConnectionStatus('Connection Failed');
        addMessage("Sorry, I'm having trouble connecting. Please try again later.", "assistant");
    }
}

function updateConnectionStatus(status) {
    const statusDisplay = document.getElementById('connection-status');
    if (statusDisplay) {
        statusDisplay.textContent = status;
        statusDisplay.classList.remove('text-green-400', 'text-yellow-400', 'text-red-400');
        if (status === 'Connected') {
            statusDisplay.classList.add('text-green-400');
        } else if (status.startsWith('Reconnecting') || status === 'Connecting...') {
            statusDisplay.classList.add('text-yellow-400');
        } else {
            statusDisplay.classList.add('text-red-400');
        }
    }
}

async function startRecording() {
    try {
        const success = await audioClient.startRecording();
        if (success) {
            isRecording = true;
            micButton.classList.add('mic-active');
            addMessage("...", "user");
        }
    } catch (error) {
        console.error('Error starting recording:', error);
    }
}

function stopRecording() {
    if (!isRecording) return;
    audioClient.stopRecording();
    isRecording = false;
    micButton.classList.remove('mic-active');
    const tempMessages = document.querySelectorAll('.user-message');
    if (tempMessages.length > 0) {
        const lastMessage = tempMessages[tempMessages.length - 1];
        if (lastMessage.textContent === '...') {
            // The "..." will be replaced by the transcript from the server.
            // If no transcript is received, the "..." will remain.
        }
    }
}

function addMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${sender}-message`;
    messageElement.textContent = text;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

window.addEventListener('load', initializeAudioClient);
