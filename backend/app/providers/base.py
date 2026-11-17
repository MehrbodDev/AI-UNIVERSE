
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def chat(self, message: str) -> str:
        """Send a message and return the AI response."""
        raise NotImplementedError
