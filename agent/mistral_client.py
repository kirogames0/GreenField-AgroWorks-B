import requests

from config import MISTRAL_API_KEY, MISTRAL_API_URL, MISTRAL_MODEL


class MistralClient:
    def __init__(self, api_key: str = MISTRAL_API_KEY, model: str = MISTRAL_MODEL, api_url: str = MISTRAL_API_URL):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url

    def chat(self, messages: list[dict], temperature: float = 0.0, max_tokens: int = 512) -> tuple[str, int]:
        if not self.api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY is not configured. Set it in your environment or .env file to enable Mistral calls."
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[MISTRAL_ERROR] Status: {response.status_code}")
            print(f"[MISTRAL_ERROR] Response: {response.text}")
            print(f"[MISTRAL_ERROR] Payload: {payload}")
            raise
        
        data = response.json()

        if not data.get("choices"):
            raise RuntimeError("Mistral response did not contain any choices")

        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "").strip()

        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens") or usage.get("prompt_tokens") or 0

        return content, int(tokens_used)
