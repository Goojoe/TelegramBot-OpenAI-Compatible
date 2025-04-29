import os
import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from app.config.config_loader import ConfigLoader
from app.api.client import OpenAIClient
from typing import Dict, Any, List

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

# 全局变量用于存储用户会话历史
user_conversations: Dict[int, Dict[str, Any]] = {}

async def is_user_authorized(user_id: int) -> bool:
    """
    检查用户是否在授权列表中。

    Args:
        user_id: Telegram用户ID

    Returns:
        如果用户已授权则返回True，否则返回False
    """
    authorized_users = config_loader.get_authorized_users()
    return user_id in authorized_users or len(authorized_users) == 0  # 如果列表为空，则允许所有用户

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

def command_handler_factory(command_config: Dict[str, Any]):
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
            await update.message.reply_text("抱歉，此命令的配置存在错误。")
        return error_handler

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the command dynamically based on config."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # 检查用户是否已授权
        if not await is_user_authorized(user_id):
            logger.warning(f"Unauthorized user {user_id} attempted to use the bot")
            await update.message.reply_text("抱歉，您没有权限使用此机器人。")
            return

        user_message = update.message.text
        # 移除命令本身，只保留参数部分
        command_parts = user_message.split(' ', 1)
        user_content = command_parts[1] if len(command_parts) > 1 else ""

        logger.info(f"Handling command for user {user_id} with config: {command_config}")

        try:
            client = await get_openai_client(endpoint_name)
        except ValueError as e:
            logger.error(f"Failed to get OpenAI client: {e}")
            await update.message.reply_text("抱歉，API连接配置出错。")
            return

        # 初始化或获取用户的对话历史
        if user_id not in user_conversations:
            user_conversations[user_id] = {
                "current_endpoint": endpoint_name,
                "current_model": model,
                "current_params": params,
                "messages": []
            }
        else:
            # 更新当前会话的模型和端点
            user_conversations[user_id]["current_endpoint"] = endpoint_name
            user_conversations[user_id]["current_model"] = model
            user_conversations[user_id]["current_params"] = params
            # 如果用户使用新命令，则清除历史会话
            user_conversations[user_id]["messages"] = []

        # 添加用户消息到会话历史
        if user_content:
            user_conversations[user_id]["messages"].append({"role": "user", "content": user_content})

        # 使用对话历史构建消息
        messages = user_conversations[user_id]["messages"]

        # 如果没有消息或消息为空，添加一个默认的用户消息
        if not messages or (len(messages) == 1 and not messages[0].get("content")):
            messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]
            user_conversations[user_id]["messages"] = messages

        try:
            # 显示输入指示器
            await context.bot.send_chat_action(chat_id=chat_id, action='typing')

            response = await client.create_chat_completion(
                model=model,
                messages=messages,
                **params # 传递配置的参数，如temperature, max_tokens
            )

            if response and response.get("choices"):
                assistant_message = response["choices"][0].get("message", {})
                reply_text = assistant_message.get("content", "抱歉，我无法获取回复。")

                # 添加助手回复到会话历史
                user_conversations[user_id]["messages"].append({"role": "assistant", "content": reply_text})

                # 限制会话历史的长度，防止过长
                if len(user_conversations[user_id]["messages"]) > 20:  # 保留最近的20条消息
                    user_conversations[user_id]["messages"] = user_conversations[user_id]["messages"][-20:]

                await update.message.reply_text(reply_text)
            else:
                logger.error(f"Invalid or empty response from API for endpoint {endpoint_name}: {response}")
                await update.message.reply_text("抱歉，我从AI服务收到了意外的响应。")

        except Exception as e:
            logger.error(f"Error during API call for endpoint {endpoint_name}: {e}", exc_info=True)
            await update.message.reply_text("抱歉，处理您的请求时出错。")

    return handler

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理非命令的普通文本消息，实现连续对话功能。
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 检查用户是否已授权
    if not await is_user_authorized(user_id):
        logger.warning(f"Unauthorized user {user_id} attempted to use the bot")
        await update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return

    # 检查用户是否有活跃的会话
    if user_id not in user_conversations:
        await update.message.reply_text("请先使用一个命令（如 /chat）来开始对话。")
        return

    user_message = update.message.text
    endpoint_name = user_conversations[user_id]["current_endpoint"]
    model = user_conversations[user_id]["current_model"]
    params = user_conversations[user_id]["current_params"]

    try:
        client = await get_openai_client(endpoint_name)
    except ValueError as e:
        logger.error(f"Failed to get OpenAI client: {e}")
        await update.message.reply_text("抱歉，API连接配置出错。")
        return

    # 添加用户消息到会话历史
    user_conversations[user_id]["messages"].append({"role": "user", "content": user_message})

    try:
        # 显示输入指示器
        await context.bot.send_chat_action(chat_id=chat_id, action='typing')

        response = await client.create_chat_completion(
            model=model,
            messages=user_conversations[user_id]["messages"],
            **params
        )

        if response and response.get("choices"):
            assistant_message = response["choices"][0].get("message", {})
            reply_text = assistant_message.get("content", "抱歉，我无法获取回复。")

            # 添加助手回复到会话历史
            user_conversations[user_id]["messages"].append({"role": "assistant", "content": reply_text})

            # 限制会话历史的长度，防止过长
            if len(user_conversations[user_id]["messages"]) > 20:  # 保留最近的20条消息
                user_conversations[user_id]["messages"] = user_conversations[user_id]["messages"][-20:]

            await update.message.reply_text(reply_text)
        else:
            logger.error(f"Invalid or empty response from API for endpoint {endpoint_name}: {response}")
            await update.message.reply_text("抱歉，我从AI服务收到了意外的响应。")

    except Exception as e:
        logger.error(f"Error during API call for endpoint {endpoint_name}: {e}", exc_info=True)
        await update.message.reply_text("抱歉，处理您的请求时出错。")

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

    # 添加文本消息处理器，实现连续对话功能
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    logger.info("Telegram Bot Application created and handlers registered.")
    return application

# Example of how to potentially run the bot (polling mode, not for FastAPI/webhook)
# if __name__ == '__main__':
#     app = create_bot_application()
#     logger.info("Starting bot in polling mode...")
#     app.run_polling()
