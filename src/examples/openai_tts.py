from pathlib import Path
from openai import OpenAI
from typing import Final

SAMPLE: Final = """
Its so nice to be here. lets go and enjoy the sun. And please lets stop fighting. i dont like that.
"""
import asyncio

from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

openai = AsyncOpenAI()

async def main() -> None:
    async with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="ash",
        input=SAMPLE,
        instructions="Speak in a annoyingly happy tone, you sound a bit crazy.",
        response_format="pcm",
    ) as response:
        await LocalAudioPlayer().play(response)

if __name__ == "__main__":
    asyncio.run(main())