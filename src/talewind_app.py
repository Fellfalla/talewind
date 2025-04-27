import asyncio
from talewind import tts
from talewind.master import create_response

print("Welcome to Talewind!")

EPILOGUE = """
Ein halbes Jahr später.
Die Stadt Spülburg glänzt wie nie zuvor — dank besserer Mülltrennung und täglicher Heldengedenkparaden.

Auf dem ehemaligen Hauptplatz wurde ein Denkmal errichtet:
Ein goldener Mülleimer, auf dessen Deckel die Statue eines Hühnchens thront, das triumphierend eine kleine Klobürste emporhält.

Detlev Wurstfinger führt jeden Samstag persönlich durch das neue Museum für Ehrenwerte Müllentsorgung.
Karl-Heinz unterhält Besucher mit spektakulär dummen Zaubershows, in denen er regelmäßig sich selbst verschwinden lässt.
Ohrwaschelsepp betreibt eine Zeppelin-Schule für schwerelos navigierende Zwerge.
Schubidu ist der Star des „Handstand-Express“, einer fahrenden Handstand-Showgruppe.

Und Sarkus Möder?
Er verkauft Mettbrote – diesmal mit Qualitätssiegel – und murmelt manchmal grimmig:
"""
audio_player = tts.create_audio_player()

async def main():
    # Initialize audio lock to serialize playback
    audio_lock = asyncio.Lock()

    async def speak_locked(text: str, voice: str, instructions: str):
        async with audio_lock:
            await tts.speak(text=text, voice=voice, instructions=instructions, audio_player=audio_player)

    # 1. Take the user input and forward it to ollama

    # # 2. Get the response from ollama
    # narrator_response = "Hi, im the narrator. Lets dive into an adventure full of chaos!"

    # # 3. Play the response using the TTS interface
    # await tts.speak(
    #     text=narrator_response,
    #     voice=tts.VOICE_NARRATOR,
    #     instructions=tts.VIBE_DUNGEON_MASTER_STRONG,
    #     audio_player=audio_player,
    # )

    while True:
        user_input = await asyncio.to_thread(input, "You: ")
        if user_input.lower() in ["exit", "quit"]:
            break


        # 5. Play the response using the TTS interface
        player_task = asyncio.create_task(
            speak_locked(
                text=user_input,
                voice=tts.VOICE_PLAYER,
                instructions="Excited and curious. Full of expectation and being adventurous.",
            )
        )

        # 4. Get the response from ollama
        print("Narrator: ", end="")
        async for chunk in create_response(user_input):
            print(chunk.content, end="", flush=True)
            # Queue narrator speech without overlapping audio
            asyncio.create_task(
                speak_locked(
                    text=chunk.content,
                    voice=tts.VOICE_NARRATOR,
                    instructions=chunk.voice,
                )
            )

        print("")

        await player_task


if __name__ == "__main__":
    asyncio.run(main())
