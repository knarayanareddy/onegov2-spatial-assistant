import uuid

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "qwen3-coder-30b-a3b-instruct"
    session_id: uuid.UUID | None = None
