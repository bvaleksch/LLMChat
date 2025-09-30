import random
from typing import List, Optional, Dict, Any
from .mytypes import Role
from .images import Image, GenImage

class Message:
    def __init__(self, role: Role, text: str, images: Optional[List[Image]] = None):
        self.text: str = text
        self.images: List[Image] = [] if images is None else images
        self.role: Role = role

    def attach_image(self, img: Image) -> None:
        self.images.append(img)

    def get_text(self) -> str:
        return self.text

    @staticmethod
    def _image2dict(img: Image) -> Dict[str, Any]:
        return {
            "type": "input_image",
            "image_url": f"data:image/{img.output_format};base64,{img.data}",
        }

    def get_input(self) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []
        for img in self.images:
            content.append(self._image2dict(img))
        if self.text:
            content.append({"type": "input_text", "text": self.text})
        return [{"role": str(self.role), "content": content}]

    @classmethod
    def from_result(cls, result, role: Role = Role.BOT) -> "Message":
        text = result.final_output if isinstance(result.final_output, str) else ""
        mess = Message(role, text)
        for item in getattr(result, "new_items", []):
            if (
                getattr(item, "type", None) == "tool_call_item"
                and getattr(item, "raw_item", None)
                and item.raw_item.type == "image_generation_call"
                and item.raw_item.result
            ):
                # Save with a randomized prefix to avoid collisions
                img = GenImage.from_item(item)
                img.save("test" + str(random.randint(0, 2**32 - 1)))
                mess.attach_image(img)
        return mess

    def __str__(self) -> str:
        base = f"Role: {self.role}\nText: {self.text}"
        if self.images:
            base += "Images: " + " ".join([str(img) for img in self.images])
        return base

