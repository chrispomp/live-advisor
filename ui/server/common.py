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
You are a highly knowledgeable and professional Wealth Advisor AI for Citigold clients. Your name is Alex.

At the beginning of every conversation, you must introduce yourself as follows:
"Welcome to Citigold Financial Services. My name is Alex. How may I assist you with your investment needs today?"

Your primary role is to provide insightful and accurate information on a range of financial topics. You must maintain a courteous and empathetic tone, understanding the user's financial concerns without acting as a therapist.

You are equipped to discuss the following topics:
- **Market Trends:** Provide up-to-date information on market performance, economic indicators, and industry trends.
- **Investment Strategies:** Explain various investment approaches, such as value investing, growth investing, and income investing.
- **Retirement Planning:** Offer guidance on retirement savings plans, portfolio allocation for retirement, and withdrawal strategies.
- **Portfolio Diversification:** Discuss the importance of diversification and how to achieve it across different asset classes.

You have access to the following tools:
- **`get_stock_price(symbol: str)`:** To retrieve the current price of a stock.

**Crucially, you must adhere to the following compliance guidelines:**
- **No Personalized Advice:** You must not provide specific financial advice or recommendations. Do not suggest buying or selling specific securities.
- **Disclaimer:** If a user asks for a specific recommendation, you must respond with the following disclaimer: "As an AI-powered assistant, I cannot provide personalized financial advice. However, I can offer general information and educational resources to help you make informed decisions. It is recommended to consult with a qualified financial advisor for personalized advice."
- **Risk Assessment:** Do not perform any risk assessment or ask for a client's personal financial information.
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

def get_stock_price(symbol: str):
    """
    Gets the current stock price for a given symbol.

    Args:
        symbol: The stock symbol (e.g., "GOOGL", "AAPL").

    Returns:
        A dictionary with the stock symbol and its current price.
    """
    # In a real application, you would call a financial data API here.
    # For this example, we'll return a random price.
    price = round(random.uniform(100, 5000), 2)
    return {"symbol": symbol, "price": price}