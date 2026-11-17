
import httpx

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen3:4b"


async def chat_with_ollama(message: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "/no_think\nفقط پاسخ نهایی را به زبان فارسی بده. متن تحلیل داخلی را نمایش نده. پاسخ را کوتاه و مستقیم بنویس.",
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        "stream": False,
        "think": False,
        "options": {
            "num_predict": 256,
        },
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data.get("message", {}).get("content", "").strip()

        if not content:
            raise ValueError("The AI model returned an empty response.")

        return content
