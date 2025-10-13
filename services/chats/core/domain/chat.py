import uuid
from typing import Optional, Union
from .mytypes import Role
from .message import Message
from ..adapters.openai_runner import build_agent, run_turn

class Chat:
    def __init__(self, name: str, previous_response_id: Optional[str] = None):
        self.uuid: uuid.UUID = uuid.uuid4()
        self.previous_response_id: Optional[str] = previous_response_id
        self.name: str = name
        self.agent = build_agent()

    async def send(self, message: Union[str, Message]) -> Message:
        if isinstance(message, Message):
            inp = await message.get_input()
            result = await run_turn(self.agent, inp, self.previous_response_id)
            self.previous_response_id = getattr(result, "last_response_id", None)
            return Message.from_result(result, role=Role.ASSISTANT)
        # Auto-wrap plain text
        return await self.send(Message(Role.USER, text=str(message)))
