import base64
import uuid
from typing import Optional
from PIL import Image as PILImage

class Image:
    def __init__(self, data: str, output_format: str, size: str) -> None:
        self.uuid: uuid.UUID = uuid.uuid4()
        self.type: str = "BaseImage"
        self.data: str = data
        self.output_format: str = output_format
        self.size: str = size
        self.path: Optional[str] = None

    def save(self, directory: str = "") -> None:
        path: str = directory + self.uuid.hex + "." + self.output_format
        with open(path, "wb") as file:
            file.write(base64.b64decode(self.data))
        self.path = path

    def get_path(self) -> Optional[str]:
        return self.path

    def __str__(self) -> str:
        return f"{self.type}(path={self.get_path()})"

class GenImage(Image):
    def __init__(self, quality: str, prompt: str, data: str, output_format: str, size: str) -> None:
        super().__init__(data=data, output_format=output_format, size=size)
        self.type = "GenImage"
        self.quality: str = quality
        self.prompt: str = prompt

    @classmethod
    def from_item(cls, item) -> "GenImage":
        return cls(
            quality=item.raw_item.quality,
            prompt=item.raw_item.revised_prompt,
            data=item.raw_item.result,
            output_format=item.raw_item.output_format,
            size=item.raw_item.size,
        )

    def get_prompt(self) -> str:
        return self.prompt

    def __str__(self) -> str:
        return f"{self.type}(path={self.get_path()}, prompt={self.get_prompt()})"

class InputImage(Image):
    def __init__(self, data: str, output_format: str, size: str) -> None:
        super().__init__(data, output_format, size)
        self.type = "InputImage"

    @classmethod
    def load_from_file(cls, path: str) -> "InputImage":
        img: PILImage = PILImage.open(path)
        w, h = img.size
        size: str = f"{w}x{h}"
        output_format: str = path.split(".")[-1]
        with open(path, "rb") as file:
            data: str = base64.b64encode(file.read()).decode("utf-8")
        return cls(data, output_format, size)

