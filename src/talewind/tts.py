from typing import Final, Any

import asyncio

from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

openai = AsyncOpenAI()

VOICE_NARRATOR: Final = "ash"
VOICE_PLAYER: Final = "echo"

VIBE_DUNGEON_MASTER_DEFAULT: Final = """
Voice: Warm, empathetic, and professional, reassuring the customer that their issue is understood and will be resolved.

Punctuation: Well-structured with natural pauses, allowing for clarity and a steady, calming flow.

Delivery: Calm and patient, with a supportive and understanding tone that reassures the listener.

Phrasing: Clear and concise, using customer-friendly language that avoids jargon while maintaining professionalism.

Tone: Empathetic and solution-focused, emphasizing both understanding and proactive assistance.
"""
VIBE_DUNGEON_MASTER_STRONG: Final = """
Agressive and shouting like a metal singer.
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
    async with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        instructions=instructions,
        response_format="pcm",
    ) as response:
        await audio_player.play(response)
