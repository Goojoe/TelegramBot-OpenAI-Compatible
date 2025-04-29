import os
import uvicorn
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application
from app.bot.main import create_bot_application, api_clients # Import necessary components
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Define a base URL for your webhook. Use environment variable or a default.
# For Hugging Face Spaces, this might be dynamically set.
# Example: https://your-space-name.hf.space
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "http://localhost:8000") # Default for local testing
WEBHOOK_PATH = f"/webhook/{TELEGRAM_BOT_TOKEN}" # Unique path per bot token
WEBHOOK_URL = f"{WEBHOOK_BASE_URL.rstrip('/')}{WEBHOOK_PATH}"

# --- FastAPI App Initialization ---
app = FastAPI()
ptb_app: Application = None # Placeholder for the python-telegram-bot Application

@app.on_event("startup")
async def startup_event():
    """
    Initialize the bot application and set the webhook on startup.
    """
    global ptb_app
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Cannot start the bot.")
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")

    try:
        ptb_app = create_bot_application()
        # Important: Initialize the application first to register handlers etc.
        await ptb_app.initialize()

        # Set the webhook
        logger.info(f"Setting webhook to: {WEBHOOK_URL}")
        await ptb_app.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=Update.ALL_TYPES)
        logger.info("Webhook successfully set.")

    except Exception as e:
        logger.error(f"Failed to initialize bot or set webhook: {e}", exc_info=True)
        # Depending on the deployment, you might want to exit or handle this differently
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown: remove webhook and close API clients.
    """
    if ptb_app:
        logger.info("Removing webhook...")
        try:
            await ptb_app.bot.delete_webhook()
            logger.info("Webhook removed.")
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}", exc_info=True)

        # Shutdown the PTB application gracefully
        await ptb_app.shutdown()
        logger.info("PTB Application shut down.")

    # Close all cached OpenAI clients
    logger.info("Closing OpenAI API clients...")
    for client in api_clients.values():
        try:
            await client.close()
        except Exception as e:
            logger.error(f"Error closing API client: {e}", exc_info=True)
    logger.info("API clients closed.")


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """
    Handle incoming updates from Telegram via webhook.
    """
    if not ptb_app:
        logger.error("Bot application not initialized.")
        return Response(status_code=500) # Internal Server Error

    try:
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=ptb_app.bot)
        logger.debug(f"Received update: {update}")
        await ptb_app.process_update(update)
        return Response(status_code=200) # OK
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return Response(status_code=500) # Internal Server Error

@app.get("/")
async def root():
    """
    Root endpoint for health checks or basic info.
    """
    return {"status": "Bot is running"}

# --- Running the App (for local development) ---
if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        print("Please create a .env file with TELEGRAM_BOT_TOKEN='your_token'")
    else:
        print(f"Starting FastAPI server on http://localhost:8000")
        print(f"Webhook URL configured (for setting): {WEBHOOK_URL}")
        print("Note: For local testing, you might need a tool like ngrok to expose localhost.")
        uvicorn.run(app, host="0.0.0.0", port=7860)
