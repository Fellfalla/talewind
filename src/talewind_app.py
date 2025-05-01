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

    # NOTE: create class for task queues, which makes sure they are worked off in order and cleaned properly
    narrator_tasks = []

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
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            ##### Play the response using the TTS interface

            ##### Get the game master response
            print("Narrator: ", end="")
            total_message = ""
            async for chunk in create_response(user_input):
                print(chunk.content, end="", flush=True)
                # NOTE: find a way to have coherent voice style accross sentences in chunk mode
                total_message += chunk.content

            # wait for previous narrator tasks to finish
            await asyncio.gather(*narrator_tasks, return_exceptions=True)
            narrator_tasks.clear()

            # Queue narrator speech without overlapping audio
            narrator_tasks.append(
                asyncio.create_task(
                    tts.speak(
                        text=total_message,
                        voice=tts.VOICE_NARRATOR,
                        instructions=chunk.voice,
                        audio_player=audio_player,
                    )
                )
            )

            print("")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main())
