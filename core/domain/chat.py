import uuid
from typing import Optional, Union
from core.domain.mytypes import Role
from core.domain.message import Message
from core.adapters.openai_runner import build_agent, run_turn

class Chat:
    def __init__(self, name: str):
        self.uuid: uuid.UUID = uuid.uuid4()
        self.previous_response_id: Optional[str] = None
        self.name: str = name
        self.agent = build_agent()

    async def send(self, message: Union[str, Message]) -> Message:
        if isinstance(message, Message):
            result = await run_turn(self.agent, message.get_input(), self.previous_response_id)
            self.previous_response_id = getattr(result, "last_response_id", None)
            return Message.from_result(result, role=Role.BOT)
        # Auto-wrap plain text
        return await self.send(Message(Role.USER, text=str(message)))
