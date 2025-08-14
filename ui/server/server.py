import asyncio
import json
import base64
import random

# Import Google ADK components
from google.adk.agents import Agent, LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Import common components
from common import (
    BaseWebSocketServer,
    logger,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
)

# Optimized System Instruction for a Citi Wealth Advisor
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
- **`get_order_status(order_id: str)`:** To retrieve the status of a trade or transaction.


**Crucially, you must adhere to the following compliance guidelines:**
- **No Personalized Advice:** You must not provide specific financial advice or recommendations. Do not suggest buying or selling specific securities.
- **Disclaimer:** If a user asks for a specific recommendation, you must respond with the following disclaimer: "As an AI-powered assistant, I cannot provide personalized financial advice. However, I can offer general information and educational resources to help you make informed decisions. It is recommended to consult with a qualified financial advisor for personalized advice."
- **Risk Assessment:** Do not perform any risk assessment or ask for a client's personal financial information.
"""


# Mock function for get_order_status
def get_order_status(order_id: str):
    """
    Get the current status and details of an order.

    Args:
        order_id: The order ID to look up.

    Returns:
        Dictionary containing order status details
    """
    # This is a mock function. In a real application, this would query a database.
    return {
        "order_id": order_id,
        "status": random.choice(["processing", "shipped", "delivered"]),
        "order_date": "2024-05-20",
    }


# New mock function for get_stock_price
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
    logger.info(f"Retrieved mock price for {symbol}: ${price}")
    return {"symbol": symbol, "price": price}


class LiveAPIWebSocketServer(BaseWebSocketServer):
    """WebSocket server implementation using Google ADK."""

    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__(host, port)

        # Initialize ADK components with updated instructions and tools
        self.agent = Agent(
            name="wealth_advisor_agent",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=[get_order_status, get_stock_price],
        )

        # Create session service
        self.session_service = InMemorySessionService()

    async def process_audio(self, websocket, client_id):
        # Store reference to client
        self.active_clients[client_id] = websocket

        # Create session for this client
        session = self.session_service.create_session(
            app_name="wealth_advisor_assistant",
            user_id=f"user_{client_id}",
            session_id=f"session_{client_id}",
        )

        # Create runner
        runner = Runner(
            app_name="wealth_advisor_assistant",
            agent=self.agent,
            session_service=self.session_service,
        )

        # Create live request queue
        live_request_queue = LiveRequestQueue()

        # Create run config with audio settings
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                )
            ),
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        # Queue for audio data from the client
        audio_queue = asyncio.Queue()

        async with asyncio.TaskGroup() as tg:
            # Task to process incoming WebSocket messages
            async def handle_websocket_messages():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "audio":
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            await audio_queue.put(audio_bytes)
                        elif data.get("type") == "end":
                            logger.info("Received end signal from client")
                        elif data.get("type") == "text":
                            logger.info(f"Received text: {data.get('data')}")
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            # Task to process and send audio to Gemini
            async def process_and_send_audio():
                while True:
                    data = await audio_queue.get()
                    live_request_queue.send_realtime(
                        types.Blob(
                            data=data,
                            mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                        )
                    )
                    audio_queue.task_done()

            # Task to receive and process responses
            async def receive_and_process_responses():
                interrupted = False
                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    event_str = str(event)

                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send(json.dumps({"type": "audio", "data": b64_audio}))
                            if hasattr(part, "text") and part.text:
                                if "partial=True" in event_str:
                                    await websocket.send(json.dumps({"type": "text", "data": part.text}))

                    if event.interrupted and not interrupted:
                        logger.info("🤐 INTERRUPTION DETECTED")
                        await websocket.send(json.dumps({
                            "type": "interrupted",
                            "data": "Response interrupted by user input"
                        }))
                        interrupted = True

                    if event.turn_complete:
                        if not interrupted:
                            logger.info("✅ Gemini done talking")
                            await websocket.send(json.dumps({"type": "turn_complete"}))
                        interrupted = False

            # Start all tasks
            tg.create_task(handle_websocket_messages())
            tg.create_task(process_and_send_audio())
            tg.create_task(receive_and_process_responses())


async def main():
    """Main function to start the server"""
    server = LiveAPIWebSocketServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting application via KeyboardInterrupt...")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        import traceback
        traceback.print_exc()