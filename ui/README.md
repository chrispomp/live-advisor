# ADK Multimodal Audio Agent

This project demonstrates a bidirectional audio agent powered by Google's Gemini Flash 1.5 model and the Google Agent Development Kit (ADK). It features a web-based interface where all audio processing, including recording and playback, is handled on the client-side.

## Project Structure

- `server/server.py`: The core WebSocket server implementation using the Google ADK.
- `server/tools.py`: Defines the tools available to the agent (e.g., portfolio lookup, news).
- `server/common.py`: Shared utilities and configuration.
- `client/audio-client.js`: Client-side JavaScript for handling audio and WebSocket communication.
- `client/index.html`: The main web interface.
- `server/requirements.txt`: Python dependencies.

## Key Features

- **Google ADK Implementation**: Built with the official agent-based framework.
- **Client-Side Audio Handling**: No server-side audio libraries are needed, simplifying deployment.
- **Bidirectional Audio Conversations**: Real-time, back-and-forth conversation with the Gemini model.
- **Function Calling**: The agent can use tools to retrieve information (e.g., check portfolio status).
- **Interruption Handling**: Users can interrupt the agent while it's speaking.
- **Session Management**: Tracks conversation state with a session ID.
- **Real-time Transcription**: Displays transcriptions of both user and agent speech.

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r server/requirements.txt
```

### 2. Configure Environment Variables

The application requires a Google Cloud Project ID and an Alpha Vantage API key for the news tool. Set these in your environment:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
```

### 3. Start the WebSocket Server

```bash
python server/server.py
```

The server will start and listen for WebSocket connections on port 8080.

### 3. Open the Web Interface

Open `client/index.html` in your web browser. You can use any web server, or simply open the file directly:

```bash
# Using Python's built-in HTTP server
python -m http.server 8000
```

Then navigate to `http://localhost:8000/client/index.html` in your browser.

## Using the Application

1. Click the microphone button in the chat interface to start recording
2. Speak into your microphone
3. Click the button again to stop recording and send the audio to Gemini
4. Gemini will respond with audio that plays automatically
5. The conversation will continue back and forth
6. You can see the session ID at the top of the chat window, showing persistence

## Technologies Used

- **Python**
  - WebSockets for real-time communication
  - Google Generative AI library for Gemini integration
  - Google ADK for agent-based implementation

- **JavaScript**
  - Web Audio API for capturing and playing audio
  - WebSockets for communication with the server
  - Modern JavaScript (ES6+) for the client implementation

- **HTML/CSS**
  - Tailwind CSS for the UI
  - Responsive design for different screen sizes

## Troubleshooting

- **Microphone Access**: Ensure your browser has permission to access your microphone
- **WebSocket Connection**: Check that the server is running and accessible (default: ws://localhost:8080)
- **Audio Issues**: Verify that your microphone and speakers are working correctly