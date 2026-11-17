
from app.providers.base import BaseProvider


class MockProvider(BaseProvider):
    provider_name = "mock"
    model_name = "mock-v1"

    async def chat(self, message: str) -> str:
        message = message.strip()

        if not message:
            raise ValueError("Message cannot be empty.")

        return (
            "Hello! This is the AI UNIVERSE Mock Provider.\n\n"
            f"You sent: {message}\n\n"
            "The provider system is working correctly."
        )
