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
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        # 4. Get the response from ollama
        narrator_response = f"User said: {user_input}. Now, let me respond to that."

        # 5. Play the response using the TTS interface
        await tts.speak(
            text=user_input,
            voice=tts.VOICE_PLAYER,
            instructions="Excited and curious. Full of expectation and being adventurous.",
            audio_player=audio_player,
        )

        print("Narrator: ", end="")
        async for chunk in create_response(narrator_response):
            print(chunk.content, end="", flush=True)
            await tts.speak(
                text=chunk.content,
                voice=tts.VOICE_NARRATOR,
                instructions=chunk.voice,
                audio_player=audio_player,
            )
        print("")

if __name__ == "__main__":
    asyncio.run(main())