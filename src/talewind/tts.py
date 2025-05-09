import asyncio
from typing import Any, Final

from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer
import openai

async_openai = AsyncOpenAI()

VOICE_NARRATOR: Final = "ash"
VOICE_PLAYER: Final = "echo"

TONALITY_NARRATOR_DEFAULT: Final = """
Roll every single R and keep medieval literal pronounciation. 
Tonality is based on the content: informative, mysterious, joking, or tense.
Pacing is fast and with few strategic pauses.
"""


class LockedAudioPlayer:
    """todo: create based class for audio player"""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.audio_player = LocalAudioPlayer()

    async def play(self, response: Any) -> None:
        async with self.lock:
            await self.audio_player.play(response)


def create_audio_player() -> LockedAudioPlayer:
    return LockedAudioPlayer()


async def speak(text: str, instructions: str, voice: str, audio_player: LockedAudioPlayer) -> None:
    try:
        async with async_openai.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
            instructions=instructions,
            response_format="pcm",
        ) as response:
            await audio_player.play(response)
    except openai.APIConnectionError as e:
        print(f"[ERROR] {e}")
