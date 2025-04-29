import httpx
from typing import Dict, Any, Optional

class OpenAIClient:
    """
    Client for interacting with OpenAI-compatible APIs.
    """

    def __init__(self, api_key: str, base_url: str):
        """
        Initialize the OpenAI client.

        Args:
            api_key: The API key for authentication.
            base_url: The base URL of the OpenAI-compatible API endpoint.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')  # Ensure no trailing slash
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

    async def create_chat_completion(self, model: str, messages: list, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Create a chat completion using the specified model and messages.

        Args:
            model: The model name to use.
            messages: A list of message objects (e.g., [{"role": "user", "content": "Hello"}]).
            **kwargs: Additional parameters for the API request (e.g., temperature, max_tokens).

        Returns:
            The API response dictionary or None if an error occurred.
        """
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response.json()
        except httpx.RequestError as e:
            print(f"An error occurred while requesting {e.request.url!r}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"Error response {e.response.status_code} while requesting {e.request.url!r}: {e.response.text}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    async def close(self):
        """
        Close the HTTP client.
        """
        await self.client.aclose()
