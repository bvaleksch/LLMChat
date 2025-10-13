from agents import ImageGenerationTool

def image_generation_tool() -> ImageGenerationTool:
    return ImageGenerationTool(tool_config={"type": "image_generation", "quality": "low"})
