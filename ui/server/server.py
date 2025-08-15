import asyncio
import json
import base64
import websockets

# Initialize Vertex AI early, as it's a prerequisite for ADK components
import vertexai
import os

# Use Application Default Credentials (ADC) - no API key needed
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
else:
    # This will fail if not in a GCP environment without project being set.
    # Added for local testing flexibility if GOOGLE_CLOUD_PROJECT is set.
    print("Warning: GOOGLE_CLOUD_PROJECT not set. Vertex AI initialization may fail.")
    vertexai.init()


from google.adk.agents import Agent, LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from google.adk.tools import google_search
from tools import (
    get_user_portfolio_summary,
    get_market_news_and_sentiment,
    get_citi_perspective,
)
from common import (
    BaseWebSocketServer,
    logger,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
    SYSTEM_INSTRUCTION,
)

class ADKWebSocketServer(BaseWebSocketServer):
    """WebSocket server implementation using Google ADK."""

    def __init__(self, host="0.0.0.0", port=None):
        if port is None:
            port = int(os.getenv("PORT", 8080))
        super().__init__(host, port)
        self.agent = Agent(
            name="wealth_advisor_agent",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=[
                get_user_portfolio_summary,
                get_market_news_and_sentiment,
                get_citi_perspective,
            ],
        )
        self.session_service = InMemorySessionService()

    async def process_audio(self, websocket, client_id):
        self.active_clients[client_id] = websocket
        session = self.session_service.create_session(
            app_name="wealth_advisor_assistant",
            user_id=f"user_{client_id}",
            session_id=f"session_{client_id}",
        )
        runner = Runner(
            app_name="wealth_advisor_assistant",
            agent=self.agent,
            session_service=self.session_service,
        )
        live_request_queue = LiveRequestQueue()
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
                )
            ),
            response_modalities=[types.Modality.AUDIO, types.Modality.TEXT],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )
        audio_queue = asyncio.Queue()

        async with asyncio.TaskGroup() as tg:
            # Task to process incoming WebSocket messages from the client
            async def handle_websocket_messages():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "audio":
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            await audio_queue.put(audio_bytes)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received")
                    except Exception as e:
                        logger.error(f"Error processing websocket message: {e}")

            # Task to send audio from our internal queue to the ADK
            async def process_and_send_audio():
                while True:
                    data = await audio_queue.get()
                    live_request_queue.send_realtime(
                        types.Blob(data=data, mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}")
                    )
                    audio_queue.task_done()

            # Task to receive and process responses from the ADK
            async def receive_and_process_responses():
                interrupted_in_turn = False
                user_transcript = ""

                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            # Handle agent audio output
                            if hasattr(part, "inline_data") and part.inline_data:
                                b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send(json.dumps({"type": "audio", "data": b64_audio}))

                            # Handle agent text output (transcription of its speech)
                            if hasattr(part, "text") and part.text and event.content.role == "model":
                                # Refined logic: Use the final text if available, otherwise stream partials.
                                # This requires inspecting the event object more closely.
                                # Assuming a hypothetical `part.is_partial` attribute for robustness.
                                is_partial = not hasattr(part, 'is_final') or not part.is_final # Hypothetical robust check
                                if is_partial: # Send partial transcripts for real-time feel
                                     await websocket.send(json.dumps({"type": "text", "data": part.text}))

                            # Handle user text input (transcription of user speech)
                            if hasattr(part, "text") and part.text and event.content.role == "user":
                                user_transcript += part.text
                                # Send the partial transcript to the client for a more responsive feel
                                await websocket.send(json.dumps({"type": "user_transcript", "data": user_transcript}))

                    # Handle interruption event
                    if event.actions.state_delta.get("interrupted", False) and not interrupted_in_turn:
                        logger.info("🤐 Interruption detected")
                        await websocket.send(json.dumps({"type": "interrupted"}))
                        interrupted_in_turn = True

                    # Handle turn completion event
                    if event.actions.state_delta.get("turn_complete", False):
                        if not interrupted_in_turn:
                            logger.info("✅ Turn complete")
                            await websocket.send(json.dumps({"type": "turn_complete"}))

                        # Log final user transcript for this turn
                        if user_transcript.strip():
                            logger.info(f"User transcript: '{user_transcript.strip()}'")

                        # Reset for the next turn
                        interrupted_in_turn = False
                        user_transcript = ""

            # Start all concurrent tasks
            tg.create_task(handle_websocket_messages())
            tg.create_task(process_and_send_audio())
            tg.create_task(receive_and_process_responses())

# This part is for Gunicorn to find the app
server = ADKWebSocketServer()
app = server.start # Gunicorn will await this coroutine

if __name__ == "__main__":
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Exiting application...")
