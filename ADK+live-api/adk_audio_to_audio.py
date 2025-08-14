import asyncio
import random
import pyaudio
from collections import deque
import os
from dotenv import load_dotenv

from google.adk.agents import Agent, LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.genai import types
from google.adk.tools import google_search

# For Vertex AI setup
import vertexai
from vertexai.generative_models import GenerationConfig

# Load environment variables from .env file
load_dotenv()

# Audio configuration
FORMAT = pyaudio.paInt16
RECEIVE_SAMPLE_RATE = 24000
SEND_SAMPLE_RATE = 16000
CHUNK_SIZE = 512
CHANNELS = 1

# Project configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "fsi-banking-agentspace")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = "gemini-2.0-flash-live-preview-04-09"
VOICE_NAME = "Aoede"

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

print(f"Initialized Vertex AI with project: {PROJECT_ID}, location: {LOCATION}")


def load_system_instruction(default_filepath="system_prompt.txt"):
    """
    Loads the system instruction from a file.
    Constructs a path to the file relative to the script's location,
    making it robust to the execution directory.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, default_filepath)
        with open(filepath, "r") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: System instruction file not found at {filepath}")
        return ""
    except Exception as e:
        print(f"Error loading system instruction: {e}")
        return ""


SYSTEM_INSTRUCTION = load_system_instruction()


class AudioManager:
    """Handles audio input and output using PyAudio."""

    def __init__(self, input_sample_rate=16000, output_sample_rate=24000):
        self.pya = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        self.audio_queue = deque()
        self.playback_task = None

    async def initialize(self):
        """Initializes audio streams."""
        mic_info = self.pya.get_default_input_device_info()
        print(f"Using microphone: {mic_info['name']}")

        self.input_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=self.input_sample_rate,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        self.output_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=self.output_sample_rate,
            output=True,
        )

    def add_audio(self, audio_data):
        """Adds audio data to the playback queue."""
        self.audio_queue.append(audio_data)
        if self.playback_task is None or self.playback_task.done():
            self.playback_task = asyncio.create_task(self.play_audio())

    async def play_audio(self):
        """Plays all queued audio data."""
        print("🗣️  Alex is talking...")
        while self.audio_queue:
            try:
                audio_data = self.audio_queue.popleft()
                await asyncio.to_thread(self.output_stream.write, audio_data)
            except Exception as e:
                print(f"Error playing audio: {e}")

    def interrupt(self):
        """Handles interruption by stopping playback and clearing the queue."""
        self.audio_queue.clear()
        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()


def setup_agent_and_runner():
    """Creates and configures the ADK agent, session, and runner."""
    agent = Agent(
        name="wealth_advisor_agent",
        model=MODEL,
        instruction=SYSTEM_INSTRUCTION,
        tools=[google_search],
    )

    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name="wealth-advisor-app",
        user_id="test_user",
        session_id="wealth-advisor-session",
    )

    runner = Runner(
        app_name="wealth-advisor-app",
        agent=agent,
        session_service=session_service,
    )
    return runner, session


def create_run_config():
    """Creates the run configuration for the agent."""
    return RunConfig(
        streaming_mode=StreamingMode.BIDI,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
            )
        ),
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )


async def audio_loop():
    """Main loop for capturing, processing, and responding to audio."""
    audio_manager = AudioManager(
        input_sample_rate=SEND_SAMPLE_RATE, output_sample_rate=RECEIVE_SAMPLE_RATE
    )
    await audio_manager.initialize()

    runner, session = setup_agent_and_runner()
    run_config = create_run_config()
    live_request_queue = LiveRequestQueue()
    audio_queue = asyncio.Queue()

    async def listen_for_audio():
        """Captures audio from the microphone and puts it in a queue."""
        while True:
            data = await asyncio.to_thread(
                audio_manager.input_stream.read, CHUNK_SIZE, exception_on_overflow=False
            )
            await audio_queue.put(data)

    async def process_and_send_audio():
        """Sends audio from the queue to the agent."""
        while True:
            data = await audio_queue.get()
            live_request_queue.send_realtime(
                types.Blob(data=data, mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}")
            )
            audio_queue.task_done()

    async def receive_and_process_responses():
        """Receives and processes responses from the agent."""
        async for event in runner.run_live(
            session=session,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        audio_manager.add_audio(part.inline_data.data)
                    if hasattr(part, "text") and part.text:
                        print(f"Transcript: {part.text}")

            if event.actions.state_delta.get("turn_complete", False):
                print("✅ Turn complete")
            if event.actions.state_delta.get("interrupted", False):
                print("🤐 Interruption detected")
                audio_manager.interrupt()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(listen_for_audio())
        tg.create_task(process_and_send_audio())
        tg.create_task(receive_and_process_responses())


if __name__ == "__main__":
    try:
        asyncio.run(audio_loop(), debug=True)
    except KeyboardInterrupt:
        print("\nExiting application...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()