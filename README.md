# 支持 OpenAI 兼容 API 的 Telegram 机器人

本项目提供了一个使用 Python、FastAPI 和 `python-telegram-bot` 构建的 Telegram 机器人框架。它允许您连接到多个 OpenAI 兼容的 API 端点（包括自定义或自托管的端点），并在 Telegram 中定义自定义斜杠命令，每个命令都链接到特定的 API 配置（端点、模型、参数）。

## 功能特性

-   **多 API 支持：** 同时配置和使用不同的 OpenAI 兼容 API。
-   **YAML 配置：** 在 `bot_config.yaml` 文件中轻松定义 API 端点和命令行为。
-   **环境变量集成：** 使用 `.env` 文件安全地加载敏感信息，如 API 密钥和机器人令牌。
-   **自定义斜杠命令：** 将 Telegram 斜杠命令 (`/command`) 映射到特定的 API 配置和参数。
-   **FastAPI 集成：** 作为 FastAPI Web 应用程序运行，适合使用 Webhook 进行部署。
-   **Hugging Face Spaces 适配：** 设计易于部署到 Hugging Face Spaces。

## 项目结构

```
.
├── app/                    # 主应用程序模块
│   ├── api/                # API 交互逻辑
│   │   ├── __init__.py
│   │   └── client.py       # OpenAI 兼容 API 客户端
│   ├── bot/                # Telegram 机器人逻辑
│   │   ├── __init__.py
│   │   └── main.py         # 核心机器人应用设置和命令处理
│   ├── config/             # 配置加载
│   │   ├── __init__.py
│   │   └── config_loader.py # YAML 和 .env 配置加载器
│   └── __init__.py
├── configs/                # 配置文件目录
│   └── bot_config.yaml.example # 示例配置文件
├── .env.example            # 示例环境变量文件
├── main.py                 # FastAPI 应用程序入口点 (用于 Webhook)
├── README.md               # 本文件 (中文版说明文档)
└── requirements.txt        # Python 依赖项
```

## 安装与设置

1.  **克隆仓库：**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **创建虚拟环境 (推荐)：**
    ```bash
    python -m venv venv
    # 激活环境
    # Windows (PowerShell/CMD):
    .\venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```

3.  **安装依赖：**
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置环境变量：**
    -   复制 `.env.example` 到 `.env`：
        ```bash
        # Windows
        copy .env.example .env
        # Linux/macOS
        cp .env.example .env
        ```
    -   编辑 `.env` 文件，填入您真实的 `TELEGRAM_BOT_TOKEN`。
    -   添加您配置中引用的任何 API 密钥（例如 `OPENAI_API_KEY`）。
    -   如果在 Hugging Face Spaces 之外部署或使用 `ngrok` 等工具进行本地测试，请将 `WEBHOOK_BASE_URL` 设置为您的可公开访问的 URL。

5.  **配置机器人行为：**
    -   复制 `configs/bot_config.yaml.example` 到 `configs/bot_config.yaml`：
        ```bash
        # Windows
        copy configs\bot_config.yaml.example configs\bot_config.yaml
        # Linux/macOS
        cp configs/bot_config.yaml.example configs/bot_config.yaml
        ```
    -   编辑 `configs/bot_config.yaml` 文件，定义您所需的 API 端点和命令。请参考示例文件进行配置。

## 运行机器人

### 本地开发 (使用 ngrok 或类似工具)

1.  **启动隧道服务 (如 ngrok) 以暴露本地端口 8000：**
    ```bash
    ngrok http 8000
    ```
    记下 ngrok 提供的 `https://` URL。

2.  **更新 `.env` 文件：** 将 `WEBHOOK_BASE_URL` 设置为 ngrok 提供的 HTTPS URL。

3.  **运行 FastAPI 应用：**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    机器人将启动，并使用您 `.env` 文件中的 `WEBHOOK_BASE_URL` 自动设置 Webhook。

### 部署到 Hugging Face Spaces

1.  **创建 `Dockerfile` (可选，但推荐用于 Spaces)：**
    ```dockerfile
    # 选择与您开发环境匹配的 Python 版本
    FROM python:3.10-slim

    # 设置工作目录
    WORKDIR /app

    # 复制依赖文件并安装依赖
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # 复制应用程序的其余代码
    COPY . .

    # 暴露 FastAPI 将运行的端口 (默认为 8000)
    EXPOSE 8000

    # 使用 uvicorn 运行应用程序的命令
    # HF Spaces 通常期望应用在端口 7860 上，但 uvicorn 默认为 8000。
    # 请查阅 HF 文档；您可能需要 --port 7860 或依赖它们的代理。
    # 使用 0.0.0.0 允许来自容器外部的连接。
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

2.  **创建 Hugging Face Space：**
    -   访问 [huggingface.co/new-space](https://huggingface.co/new-space)。
    -   选择 "Docker" 作为 Space SDK。
    -   选择 "Blank" 模板或提供您的 Dockerfile。
    -   配置 Space 名称和可见性。

3.  **将代码推送到 Space 仓库：**
    -   将您的 `Dockerfile` (如果创建了)、`.env` (或配置 Secrets)、`configs/bot_config.yaml` 以及所有其他项目文件添加到您的 Space 的 Git 仓库中。
    -   **重要安全提示：** 如果 `.env` 文件包含敏感密钥，请勿直接提交它。使用 Hugging Face Space 的 **Secrets** 来存储 `TELEGRAM_BOT_TOKEN`、`OPENAI_API_KEY` 等。在您的代码/配置中将这些 Secrets 作为环境变量引用。您的 `ConfigLoader` 已经支持从环境变量读取。
    -   如果使用 Secrets，则仓库中不需要 `.env` 文件。请确保您的 `bot_config.yaml` 对存储为 Secrets 的密钥使用 `${VAR_NAME}` 语法。

4.  **在 HF Spaces 中配置 Secrets：**
    -   转到您的 Space 设置 > "Secrets"。
    -   为 `TELEGRAM_BOT_TOKEN`、`OPENAI_API_KEY` 以及 `bot_config.yaml` 所需的任何其他密钥添加 Secrets。

5.  **Hugging Face 自动 Webhook URL：**
    -   Hugging Face Spaces 会自动提供一个公共 URL (例如 `https://your-user-your-space-name.hf.space`)。
    -   `main.py` 脚本尝试从环境中读取 `WEBHOOK_BASE_URL`。Hugging Face *可能* 会自动设置此变量，或者您可能需要将其添加为指向 Space 公共 URL 的 Secret。如果未设置，它将默认为 localhost，这在 Spaces 上无法工作。**请确保 `WEBHOOK_BASE_URL` 通过 HF 环境或 Secret 正确设置。**

6.  **检查日志：** 监控您的 Hugging Face Space 中的构建和运行时日志，以确保应用程序正确启动并且 Webhook 设置无误。

## 使用方法

一旦机器人运行并且 Webhook 设置成功：

-   打开 Telegram 并找到您的机器人。
-   输入您在 `configs/bot_config.yaml` 中定义的斜杠命令之一（例如 `/chat`、`/creative`）。
-   机器人将使用相应的 API 端点、模型和参数来生成响应。
