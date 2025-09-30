import asyncio
from typing import List
from dotenv import load_dotenv
from core.domain.chat import Chat
from core.domain.mytypes import Role
from core.domain.images import InputImage
from core.domain.message import Message
# Optionally reuse the “friendlier” loop we discussed earlier

load_dotenv()

async def main():
    chat = Chat("First chat")
    while True:
        user_text = input("Enter message: ")
        if user_text.lower() == "exit":
            break

        images: List[InputImage] = []
        while True:
            img_path = input("Enter path of image (leave empty if none): ").strip()
            if img_path in ["-", ""]:
                break
            images.append(InputImage.load_from_file(img_path))

        user_message = Message(Role.USER, user_text, images) 

        reply: Message = await chat.send(user_message)
        print(reply)

if __name__ == "__main__":
    asyncio.run(main())


