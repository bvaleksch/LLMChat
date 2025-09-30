from typing import Optional, Any
from agents import Agent, Runner, ModelSettings
from .image_tool import image_generation_tool

def build_agent() -> Agent:
    return Agent(
        name="Okapi",
        model="gpt-5",
        instructions="You are a helpful assistant.",
        model_settings=ModelSettings(verbosity="low"),
        tools=[image_generation_tool()],
    )

async def run_turn(agent: Agent, input_payload: Any, previous_response_id: Optional[str]) -> Any:
    return await Runner.run(agent, input=input_payload, previous_response_id=previous_response_id)
