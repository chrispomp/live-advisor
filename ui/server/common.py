import asyncio
import json
import logging
import websockets
import traceback
import os
from websockets.exceptions import ConnectionClosed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants ---
MODEL = os.getenv("ADK_MODEL", "gemini-2.0-flash-live-preview-04-09")
VOICE_NAME = "Aoede" # A professional and clear voice for the advisor

# Audio sample rates
RECEIVE_SAMPLE_RATE = 24000  # Rate of audio received from Gemini
SEND_SAMPLE_RATE = 16000     # Rate of audio sent to Gemini

def load_system_instruction(filepath="system_prompt.txt"):
    """Loads the system instruction from a file."""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Error: System instruction file not found at {filepath}")
        return "" # Return empty string to prevent crash, though agent will be uninstructed
    except Exception as e:
        logger.error(f"Error loading system instruction: {e}")
        return ""

SYSTEM_INSTRUCTION = load_system_instruction()

MANDATORY_DISCLAIMER = "I am an AI assistant. My insights are for informational purposes only and should not be considered financial advice. Please consult with a qualified financial professional."

# --- Base WebSocket Server Class ---
class BaseWebSocketServer:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = int(os.environ.get('PORT', port)) # Use PORT from env var if available
        self.active_clients = {}

    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket):
        """Handle a new WebSocket client connection"""
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")
        await websocket.send(json.dumps({"type": "ready"}))
        try:
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            if client_id in self.active_clients:
                del self.active_clients[client_id]

    async def process_audio(self, websocket, client_id):
        """Abstract method for processing audio from the client."""
        raise NotImplementedError("Subclasses must implement process_audio")