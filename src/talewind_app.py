import asyncio
from talewind import tts
from talewind.mcp_servers.mcp_facade import McpFacade
from talewind.master import Agent
from mcp_agent.core.fastagent import FastAgent
from talewind.tts import LockedAudioPlayer

audio_player = tts.create_audio_player()


class AudioRequest:
    def __init__(self, text: str, voice: str, tonality: str):
        self.text = text
        self.voice = voice
        self.tonality = tonality


tts_queue: asyncio.Queue[AudioRequest] = asyncio.Queue()


async def story_loop(agent: FastAgent):
    async with agent.run() as agent_app:
        while True:
            try:
                user_input = await asyncio.to_thread(input, "You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                ##### Play the response using the TTS interface
                await tts_queue.put(
                    AudioRequest(
                        text=user_input,
                        voice=tts.VOICE_PLAYER,
                        tonality="Naive and childish, like a child playing a game with their friends.",
                    )
                )

                ##### Get the game master response
                print("Narrator: ", end="")
                total_message = await agent_app.send(user_input, agent_name="master")
                # total_message = await agent_app.prompt("master")

                await tts_queue.put(
                    AudioRequest(
                        text=total_message,
                        voice=tts.VOICE_NARRATOR,
                        tonality=tts.VIBE_DUNGEON_MASTER_DEFAULT,
                    )
                )

                print("")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                continue


async def audio_loop(audio_player: LockedAudioPlayer):
    while True:
        audio_request = await tts_queue.get()

        # TODO: generate and replay in parallel
        await tts.speak(
            text=audio_request.text,
            voice=audio_request.voice,
            instructions=audio_request.tonality,
            audio_player=audio_player,
        )


# Create the application
fast = FastAgent("master", config_path="src/talewind/config/fast-agent.yaml")


@fast.agent(
    name="master",
    instruction=Agent.DEFAULT_SYSTEM_PROMPT,
    model="openai.gpt-4o",
    servers=["inventory", "dice"],
    human_input=True,
)
async def main():
    # Initialize audio lock to serialize playback

    audio_player = tts.create_audio_player()

    await asyncio.wait(
        [
            asyncio.create_task(story_loop(fast)),
            asyncio.create_task(audio_loop(audio_player)),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )


if __name__ == "__main__":
    asyncio.run(main())
