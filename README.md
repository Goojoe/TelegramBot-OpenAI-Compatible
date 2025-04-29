# Telegram Bot with OpenAI-Compatible API Support

This project provides a Telegram bot framework built with Python, FastAPI, and `python-telegram-bot`. It allows you to connect to multiple OpenAI-compatible API endpoints (including custom or self-hosted ones) and define custom slash commands in Telegram, each linked to a specific API configuration (endpoint, model, parameters).

## Features

-   **Multi-API Support:** Configure and use different OpenAI-compatible APIs simultaneously.
-   **YAML Configuration:** Easily define API endpoints and command behaviors in a `bot_config.yaml` file.
-   **Environment Variable Integration:** Securely load sensitive information like API keys and bot tokens using a `.env` file.
-   **Custom Slash Commands:** Map Telegram slash commands (`/command`) to specific API configurations and parameters.
-   **FastAPI Integration:** Runs as a FastAPI web application, suitable for deployment using webhooks.
-   **Hugging Face Spaces Ready:** Designed for easy deployment on Hugging Face Spaces.

## Project Structure

```
.
├── app/                    # Main application module
│   ├── api/                # API interaction logic
│   │   ├── __init__.py
│   │   └── client.py       # OpenAI-compatible API client
│   ├── bot/                # Telegram bot logic
│   │   ├── __init__.py
│   │   └── main.py         # Core bot application setup and command handling
│   ├── config/             # Configuration loading
│   │   ├── __init__.py
│   │   └── config_loader.py # YAML and .env config loader
│   └── __init__.py
├── configs/                # Configuration files directory
│   └── bot_config.yaml.example # Example configuration file
├── .env.example            # Example environment variables file
├── main.py                 # FastAPI application entry point (for webhook)
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows (PowerShell/CMD):
    .\venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    -   Copy `.env.example` to `.env`:
        ```bash
        # Windows
        copy .env.example .env
        # Linux/macOS
        cp .env.example .env
        ```
    -   Edit the `.env` file and add your actual `TELEGRAM_BOT_TOKEN`.
    -   Add any API keys referenced in your configuration (e.g., `OPENAI_API_KEY`).
    -   If deploying outside Hugging Face Spaces or testing locally with a tool like `ngrok`, set the `WEBHOOK_BASE_URL` to your publicly accessible URL.

5.  **Configure Bot Behavior:**
    -   Copy `configs/bot_config.yaml.example` to `configs/bot_config.yaml`:
        ```bash
        # Windows
        copy configs\bot_config.yaml.example configs\bot_config.yaml
        # Linux/macOS
        cp configs/bot_config.yaml.example configs/bot_config.yaml
        ```
    -   Edit `configs/bot_config.yaml` to define your desired API endpoints and commands. See the example file for guidance.

## Running the Bot

### Local Development (using ngrok or similar)

1.  **Start a tunneling service (like ngrok) to expose your local port 8000:**
    ```bash
    ngrok http 8000
    ```
    Note the `https://` URL provided by ngrok.

2.  **Update `.env`:** Set `WEBHOOK_BASE_URL` to the ngrok HTTPS URL.

3.  **Run the FastAPI application:**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    The bot will start, and the webhook will be set automatically using the `WEBHOOK_BASE_URL` from your `.env` file.

### Deployment on Hugging Face Spaces

1.  **Create a `Dockerfile` (optional but recommended for Spaces):**
    ```dockerfile
    # Choose the Python version matching your development environment
    FROM python:3.10-slim

    # Set the working directory
    WORKDIR /app

    # Copy dependency file and install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy the rest of the application code
    COPY . .

    # Expose the port FastAPI will run on (default is 8000)
    EXPOSE 8000

    # Command to run the application using uvicorn
    # HF Spaces typically expects the app on port 7860, but uvicorn defaults to 8000.
    # Check HF documentation; you might need --port 7860 or rely on their proxying.
    # Using 0.0.0.0 allows connections from outside the container.
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

2.  **Create a Hugging Face Space:**
    -   Go to [huggingface.co/new-space](https://huggingface.co/new-space).
    -   Choose "Docker" as the Space SDK.
    -   Select "Blank" template or provide your Dockerfile.
    -   Configure the Space name and visibility.

3.  **Push your code to the Space repository:**
    -   Add your `Dockerfile` (if created), `.env` (or configure secrets), `configs/bot_config.yaml`, and all other project files to the Git repository for your Space.
    -   **Important Security Note:** Do NOT commit your `.env` file directly if it contains sensitive keys. Use Hugging Face Space **Secrets** to store `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, etc. Reference these secrets in your code/config as environment variables. Your `ConfigLoader` already supports reading from environment variables.
    -   If using secrets, you don't need a `.env` file in the repository. Ensure your `bot_config.yaml` uses the `${VAR_NAME}` syntax for keys stored as secrets.

4.  **Configure Secrets in HF Spaces:**
    -   Go to your Space settings > "Secrets".
    -   Add secrets for `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, and any other keys needed by your `bot_config.yaml`.

5.  **Hugging Face Automatic Webhook URL:**
    -   Hugging Face Spaces automatically provides a public URL (e.g., `https://your-user-your-space-name.hf.space`).
    -   The `main.py` script attempts to read `WEBHOOK_BASE_URL` from the environment. Hugging Face *might* set this automatically, or you might need to add it as a Secret pointing to the Space's public URL. If not set, it defaults to localhost, which won't work on Spaces. **Ensure `WEBHOOK_BASE_URL` is correctly set either via HF environment or as a Secret.**

6.  **Check Logs:** Monitor the build and runtime logs in your Hugging Face Space to ensure the application starts correctly and the webhook is set without errors.

## Usage

Once the bot is running and the webhook is set:

-   Open Telegram and find your bot.
-   Type one of the slash commands you defined in `configs/bot_config.yaml` (e.g., `/chat`, `/creative`).
-   The bot will use the corresponding API endpoint, model, and parameters to generate a response.
