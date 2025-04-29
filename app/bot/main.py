import os
import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from app.config.config_loader import ConfigLoader
from app.api.client import OpenAIClient
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global cache for OpenAI clients (one per API endpoint config)
api_clients: Dict[str, OpenAIClient] = {}

# Global config loader instance
config_loader = ConfigLoader()

async def get_openai_client(endpoint_name: str) -> OpenAIClient:
    """
    Get or create an OpenAIClient instance for a given endpoint configuration.

    Args:
        endpoint_name: The name of the API endpoint configuration.

    Returns:
        An initialized OpenAIClient instance.

    Raises:
        ValueError: If the endpoint configuration is not found or invalid.
    """
    if endpoint_name in api_clients:
        return api_clients[endpoint_name]

    endpoint_config = config_loader.get_api_endpoint(endpoint_name)
    if not endpoint_config:
        raise ValueError(f"API endpoint configuration '{endpoint_name}' not found.")

    api_key = endpoint_config.get("api_key")
    base_url = endpoint_config.get("base_url")

    if not api_key or not base_url:
        raise ValueError(f"Invalid configuration for endpoint '{endpoint_name}': missing api_key or base_url.")

    client = OpenAIClient(api_key=api_key, base_url=base_url)
    api_clients[endpoint_name] = client
    logger.info(f"Initialized OpenAIClient for endpoint: {endpoint_name}")
    return client

async def command_handler_factory(command_config: Dict[str, Any]):
    """
    Factory function to create command handlers based on configuration.

    Args:
        command_config: Configuration dictionary for the command.

    Returns:
        An asynchronous function that acts as the command handler.
    """
    endpoint_name = command_config.get("api_endpoint")
    model = command_config.get("model")
    params = command_config.get("parameters", {})

    if not endpoint_name or not model:
        logger.error(f"Invalid command config: {command_config}. Missing 'api_endpoint' or 'model'.")
        # Return a dummy handler that logs an error
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Command configuration error for command triggered by user {update.effective_user.id}")
            await update.message.reply_text("Sorry, there was a configuration error for this command.")
        return error_handler

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the command dynamically based on config."""
        user_message = update.message.text
        # Remove the command itself from the message if needed, or handle arguments
        # For simplicity, we'll use the full message for now.
        # You might want to parse arguments like: context.args

        logger.info(f"Handling command for user {update.effective_user.id} with config: {command_config}")

        try:
            client = await get_openai_client(endpoint_name)
        except ValueError as e:
            logger.error(f"Failed to get OpenAI client: {e}")
            await update.message.reply_text("Sorry, there was an error configuring the API connection.")
            return

        # Construct messages payload for OpenAI API
        # This is a basic example; you might want conversation history management
        messages = [{"role": "user", "content": user_message}]

        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

            response = await client.create_chat_completion(
                model=model,
                messages=messages,
                **params # Pass configured parameters like temperature, max_tokens
            )

            if response and response.get("choices"):
                reply_text = response["choices"][0].get("message", {}).get("content", "Sorry, I couldn't get a response.")
                await update.message.reply_text(reply_text)
            else:
                logger.error(f"Invalid or empty response from API for endpoint {endpoint_name}: {response}")
                await update.message.reply_text("Sorry, I received an unexpected response from the AI service.")

        except Exception as e:
            logger.error(f"Error during API call for endpoint {endpoint_name}: {e}", exc_info=True)
            await update.message.reply_text("Sorry, an error occurred while processing your request.")

    return handler

async def post_init(application: Application):
    """
    Post-initialization tasks, like setting bot commands dynamically.
    """
    commands_config = config_loader.get_all_commands()
    bot_commands = []
    for command_name, config in commands_config.items():
        description = config.get("description", f"Trigger {command_name}")
        # Command name in BotCommand should not have the leading '/'
        bot_commands.append(BotCommand(command_name.lstrip('/'), description))

    if bot_commands:
        await application.bot.set_my_commands(bot_commands)
        logger.info(f"Successfully set bot commands: {bot_commands}")
    else:
        logger.warning("No commands found in configuration to set.")


def create_bot_application() -> Application:
    """
    Create and configure the Telegram Bot Application instance.
    """
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")

    application = Application.builder().token(telegram_token).post_init(post_init).build()

    # Dynamically register command handlers from config
    commands_config = config_loader.get_all_commands()
    if not commands_config:
        logger.warning("No commands defined in the configuration file.")
    else:
        for command_name, config in commands_config.items():
            # Command name for handler registration should not have the leading '/'
            handler = CommandHandler(command_name.lstrip('/'), command_handler_factory(config))
            application.add_handler(handler)
            logger.info(f"Registered handler for command: {command_name}")

    # Add a default message handler if needed (e.g., for non-command messages)
    # async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     await update.message.reply_text(f"Echo: {update.message.text}")
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Telegram Bot Application created and handlers registered.")
    return application

# Example of how to potentially run the bot (polling mode, not for FastAPI/webhook)
# if __name__ == '__main__':
#     app = create_bot_application()
#     logger.info("Starting bot in polling mode...")
#     app.run_polling()
