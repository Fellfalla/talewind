import asyncio

from talewind import tts
from talewind.master import create_response

print("Welcome to Talewind!")

audio_player = tts.create_audio_player()


async def main():
    # Initialize audio lock to serialize playback

    # NOTE: create class for task queues, which makes sure they are worked off in order and cleaned properly
    narrator_tasks = []

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
