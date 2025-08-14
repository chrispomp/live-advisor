import asyncio
import json
import base64
import logging
import websockets
import traceback
from websockets.exceptions import ConnectionClosed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
PROJECT_ID = "fsi-banking-agentspace"
LOCATION = "us-central1"
MODEL = "gemini-2.0-flash-live-preview-04-09"
VOICE_NAME = "Puck"

# Audio sample rates for input/output
RECEIVE_SAMPLE_RATE = 24000  # Rate of audio received from Gemini
SEND_SAMPLE_RATE = 16000     # Rate of audio sent to Gemini

# System instruction used by both implementations
SYSTEM_INSTRUCTION = """
You are a Wealth Advisor agent for Citi clients.
Introduce yourself at the beginning of the conversation:
"Welcome to Citigold Financial Services. My name is Joe. How may I assist you with your investment needs today?"

You must be professional, courteous, and provide insightful investment advice.
You are not a therapist, but you should be empathetic to the user's financial concerns.
You can provide information on the following topics:
- Market trends
- Investment strategies
- Retirement planning
- Portfolio diversification

You should not provide specific financial advice or recommendations without a proper risk assessment and understanding of the client's financial situation.
If the user asks for a specific recommendation, you should respond with a disclaimer, such as:
"As a large language model, I cannot provide personalized financial advice. However, I can offer general information and educational resources to help you make informed decisions. It is recommended to consult with a qualified financial advisor for personalized advice."
"""

# Base WebSocket server class that handles common functionality
class BaseWebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.active_clients = {}  # Store client websockets

    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket):
        """Handle a new WebSocket client connection"""
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")

        # Send ready message to client
        await websocket.send(json.dumps({"type": "ready"}))

        try:
            # Start the audio processing for this client
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up if needed
            if client_id in self.active_clients:
                del self.active_clients[client_id]

    async def process_audio(self, websocket, client_id):
        """
        Process audio from the client. This is an abstract method that
        subclasses must implement with their specific LLM integration.
        """
        raise NotImplementedError("Subclasses must implement process_audio")
