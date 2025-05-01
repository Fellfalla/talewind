#!/usr/bin/env python3

import os
import random
import time
import traceback  # For printing detailed errors if needed

import openai
import pyttsx3
import speech_recognition as sr
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# --- Configuration ---
LLM_MODEL = "gpt-4o"  # Or "gpt-3.5-turbo" or other compatible models
# Consider increasing history for longer games, but be mindful of token limits/cost
MAX_HISTORY_TURNS = (
    10  # How many turns (player + GM response = 1 turn pair) to remember for context
)
API_RETRY_DELAY = 5  # Seconds to wait before retrying OpenAI API call
AMBIENT_NOISE_ADJUSTMENT_DURATION = 1.5  # Seconds to listen for ambient noise

# --- Initialize Services ---
console = Console()

# OpenAI Client (Assumes OPENAI_API_KEY environment variable is set)
try:
    # Ensure you have set the OPENAI_API_KEY environment variable
    # e.g., export OPENAI_API_KEY='your-key-here' (Linux/macOS)
    # or set OPENAI_API_KEY=your-key-here (Windows cmd)
    # or $env:OPENAI_API_KEY='your-key-here' (Windows PowerShell)
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]ERROR: OPENAI_API_KEY environment variable not set.[/]")
        console.print("[yellow]Please set your OpenAI API key to use the GM features.[/]")
        exit(1)
    client = openai.OpenAI()
    # Test connection with a simple request (optional, but good practice)
    # client.models.list()
    # console.print("[green]OpenAI client initialized successfully.[/]")
except openai.AuthenticationError:
    console.print("[bold red]OpenAI Authentication Error: Invalid API key or setup.[/]")
    exit(1)
except Exception as e:
    console.print(f"[bold red]Error initializing OpenAI Client: {e}[/]")
    exit(1)

# Text-to-Speech Engine
tts_engine = None
GM_VOICE_ID = None
PLAYER_VOICE_IDS = []
try:
    tts_engine = pyttsx3.init()
    voices = tts_engine.getProperty("voices")
    if voices:
        # Very basic voice assignment - might vary wildly between systems
        GM_VOICE_ID = voices[0].id  # Often a default male voice
        PLAYER_VOICE_IDS = [v.id for v in voices[1:]]  # Use remaining voices
        if not PLAYER_VOICE_IDS:  # Fallback if only one voice exists
            PLAYER_VOICE_IDS = [GM_VOICE_ID]
        tts_engine.setProperty("rate", 180)  # Adjust speech speed (words per minute)
        # console.print("[green]TTS engine initialized.[/]")
    else:
        console.print("[yellow]No TTS voices found. Text-to-speech will be disabled.[/]")
        tts_engine = None

except Exception as e:
    console.print(f"[bold red]Error initializing TTS engine: {e}[/]")
    console.print("[yellow]Text-to-speech will be disabled.[/]")
    tts_engine = None  # Disable TTS if initialization fails

# Speech Recognition Engine
recognizer = sr.Recognizer()
microphone = None  # Initialize microphone as None FIRST
try:
    # --- TRY TO INITIALIZE MICROPHONE ---
    # This is the part that often fails in WSL or without correct drivers/permissions
    microphone = sr.Microphone()
    with microphone as source:
        console.print("[cyan]Adjusting microphone for ambient noise... Please be quiet.[/]")
        # Increase duration if needed, especially in noisy environments or with slow mics
        recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_NOISE_ADJUSTMENT_DURATION)
        console.print("[green]Microphone adjusted and ready.[/]")
except OSError as e:
    # --- HANDLE THE SPECIFIC WSL/Device ERROR ---
    if "No Default Input Device Available" in str(e) or "Invalid input device" in str(e):
        console.print("[bold yellow]WARNING: No default audio input device found or accessible.[/]")
        console.print("[yellow]This is common in WSL or if microphone permissions are denied.[/]")
        console.print(
            "[yellow]Microphone input will be disabled. Game will use TEXT INPUT instead.[/]"
        )
        microphone = None  # Ensure microphone is None if initialization failed
    else:
        # Handle other potential OS errors during microphone setup
        console.print(f"[bold red]An OS error occurred setting up the microphone: {e}[/]")
        console.print("[yellow]Microphone input will be disabled. Using TEXT INPUT instead.[/]")
        microphone = None
except AttributeError as e:
    # This can happen if PyAudio is missing or its dependencies are not met
    console.print(f"[bold red]AttributeError during microphone setup: {e}[/]")
    console.print(
        "[yellow]Ensure PyAudio is installed correctly with its system dependencies (like portaudio).[/]"
    )
    console.print("[yellow]Microphone input will be disabled. Using TEXT INPUT instead.[/]")
    microphone = None
except Exception as e:
    # Catch any other exceptions during mic setup
    console.print(f"[bold red]Could not initialize microphone: {e}[/]")
    console.print("[yellow]Microphone input will be disabled. Using TEXT INPUT instead.[/]")
    microphone = None  # Ensure microphone is None on any error


# --- Game State ---
game_state = {
    "players": [],  # List of player dictionaries: {'name': str, 'voice_id': str}
    "current_location": "a dimly lit tavern entrance in the fantasy city of Evermore",
    "world_description": "A medieval fantasy world named Eldoria, known for its floating islands, ancient elemental magic, and political intrigue between kingdoms.",
    "quest": "None currently assigned.",
    "turn": 0,
    "current_player_index": 0,
    "history": [],  # Stores tuples: {"role": "user"/"assistant", "content": text} for LLM
}

# --- Core Functions ---


def speak(text, voice_id=None):
    """Uses TTS to speak the given text with an optional specific voice."""
    if not tts_engine:
        # console.print("[italic grey](TTS disabled)[/]")
        return  # TTS disabled or failed to initialize

    try:
        current_voice = tts_engine.getProperty(
            "voice"
        )  # Get current voice to restore later if needed
        if voice_id and voice_id != current_voice:
            tts_engine.setProperty("voice", voice_id)
        elif not voice_id and GM_VOICE_ID and GM_VOICE_ID != current_voice:
            tts_engine.setProperty("voice", GM_VOICE_ID)  # Default to GM voice if available

        # console.print(f"[italic grey]Speaking...[/]") # Debug
        tts_engine.say(text)
        tts_engine.runAndWait()

        # Optional: Restore original voice if changed, though often not necessary per call
        # if voice_id and voice_id != current_voice:
        #      tts_engine.setProperty('voice', current_voice)

    except Exception as e:
        console.print(f"[bold red]TTS Error during speak(): {e}[/]")


def listen_to_mic(player_name):
    """Listens for audio via microphone or falls back to text input. Returns action string or 'quit'."""
    # --- Fallback Check ---
    if microphone is None:
        # This path is taken if microphone initialization failed during setup
        console.print("[cyan](Text Input Mode)")
        action = ""
        while not action:  # Ensure player enters something
            action = input(f"{player_name} [Type Action]> ").strip()
            if not action:
                console.print("[yellow]Please type an action.[/]")

        # Check for quit commands in text input
        if action.lower() in ["quit", "exit", "stop game", "quit game", "end game"]:
            return "quit"  # Return the special 'quit' signal
        return action

    # --- Microphone Input Logic ---
    with microphone as source:
        console.print(f"\n[bold green]{player_name}, speak your action...[/] (Listening)")

        # Announce turn using player's assigned voice if possible
        player_voice_id = game_state["players"][game_state["current_player_index"]].get("voice_id")
        if not player_voice_id and PLAYER_VOICE_IDS:  # Fallback if voice ID missing or list empty
            player_voice_id = PLAYER_VOICE_IDS[
                game_state["current_player_index"] % len(PLAYER_VOICE_IDS)
            ]
        speak(f"{player_name}, it's your turn.", player_voice_id)

        audio = None
        try:
            # Listen for speech with timeout and phrase limit
            audio = recognizer.listen(
                source, timeout=10, phrase_time_limit=20
            )  # Increased phrase limit slightly
        except sr.WaitTimeoutError:
            console.print("[yellow]No speech detected within the time limit.[/]")
            return None  # Signal to the main loop to possibly retry or ask for text
        # Add specific exception handling for potential PyAudio stream errors if they occur
        except Exception as e:
            console.print(f"[bold red]Error during listening phase (mic might have issues): {e}[/]")
            return None  # Signal error to main loop

    # --- Process Speech ---
    if audio:
        console.print("[cyan]Processing speech...[/]")
        try:
            # Using Google Web Speech API by default (requires internet)
            text = recognizer.recognize_google(audio)
            console.print(f"[green]You said:[/green] {text}")
            # Check for quit commands in recognized speech
            if text.lower() in ["quit", "exit", "stop game", "quit game", "end game"]:
                return "quit"
            return text
        except sr.UnknownValueError:
            console.print(
                "[yellow]Could not understand audio. Please try again or type your action.[/]"
            )
            speak("Sorry, I couldn't understand that. Please try again.")
            return None  # Signal to main loop to retry/ask for text
        except sr.RequestError as e:
            console.print(
                f"[bold red]Could not request results from Google Speech Recognition service; {e}[/]"
            )
            speak("Sorry, my connection to the speech service seems down.")
            # Could fallback to text input here instead of just failing the turn
            return None  # Signal error to main loop
        except Exception as e:
            console.print(
                f"[bold red]An unexpected error occurred during speech recognition: {e}[/]"
            )
            return None  # Signal error

    return None  # Should not happen if audio was captured, but as a fallback


def get_llm_response(prompt_history, player_action_text, player_name):
    """Sends context and player action to the LLM and gets the GM's response."""
    messages = [
        {"role": "system", "content": build_system_prompt()},
    ]

    # Add relevant history (limit size) - Simple turn-based limit
    history_start_index = max(
        0, len(prompt_history) - (MAX_HISTORY_TURNS * 2)
    )  # Keep last N turns (input+output pairs)
    messages.extend(prompt_history[history_start_index:])

    # Add the current player's action, clearly identifying the player
    messages.append({"role": "user", "content": f"{player_name}: {player_action_text}"})

    console.print("[cyan]Asking the AI Game Master...[/]")
    retries = 3
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.75,  # Slightly increased creativity
                max_tokens=450,  # Limit response length to prevent excessive text
                stop=None,  # Let the model decide when to stop (or define specific stop sequences if needed)
            )
            gm_response = response.choices[0].message.content.strip()

            # Basic check for empty or placeholder response
            if not gm_response or gm_response.lower() in ["...", "[generating response]", "ok."]:
                console.print("[yellow]LLM returned an empty/placeholder response. Retrying...[/]")
                time.sleep(API_RETRY_DELAY / 2)  # Shorter delay for empty response retry
                continue  # Go to next retry attempt

            return gm_response

        except openai.RateLimitError:
            console.print(
                f"[bold yellow]OpenAI API Rate Limit Exceeded. Waiting {API_RETRY_DELAY * (attempt + 1)}s and retrying...[/]"
            )
            time.sleep(API_RETRY_DELAY * (attempt + 1))
        except openai.APIError as e:
            console.print(
                f"[bold red]OpenAI API Error: {e}. Retrying in {API_RETRY_DELAY}s... (Attempt {attempt + 1}/{retries})[/]"
            )
            time.sleep(API_RETRY_DELAY)
        except Exception as e:
            console.print(
                f"[bold red]Error contacting LLM: {e}. Retrying in {API_RETRY_DELAY}s... (Attempt {attempt + 1}/{retries})[/]"
            )
            time.sleep(API_RETRY_DELAY)

    # If all retries fail
    console.print("[bold red]Failed to get response from LLM after multiple retries.[/]")
    return (
        "The Game Master seems lost in thought and cannot respond right now. "
        "Perhaps try a different action or wait a moment?"
    )


def build_system_prompt():
    """Creates the initial instruction prompt for the AI Game Master."""
    player_names = [p["name"] for p in game_state["players"]]
    player_list_str = ", ".join(player_names) if player_names else "the player(s)"
    prompt = (
        f"You are the Game Master (GM) for a cooperative, text-based medieval fantasy RPG. "
        f"The world is '{game_state['world_description']}'.\n"
        f"The active players are: {player_list_str}. They are currently located at/near: '{game_state['current_location']}'.\n"
        f"The current overarching quest is: '{game_state['quest']}'.\n\n"
        "Your primary responsibilities are:\n"
        "1.  **Narrate:** Describe the environment, events, and the results of player actions vividly and engagingly. Immerse the players in the world.\n"
        "2.  **Control NPCs:** Roleplay any Non-Player Characters (NPCs) the players encounter. Give them distinct personalities and realistic reactions. Prefix NPC dialogue clearly (e.g., 'Guard Captain: Halt! Who goes there?').\n"
        "3.  **Manage World State:** Interpret player actions and describe how they affect the world, their location, inventory (implicitly), and relationships with NPCs. Keep the narrative consistent.\n"
        "4.  **Drive the Story:** Introduce challenges, puzzles, plot hooks, interesting encounters, and consequences based on player choices. Ensure the game progresses and doesn't stall.\n"
        "5.  **Respond Directly:** Your response should directly address the latest action taken by the player (indicated by 'Player Name: action text' in the user message).\n"
        "6.  **Maintain Character:** Act solely as the GM. Do NOT mention being an AI, LLM, or language model. Do not break the fourth wall unless specifically prompted in a meta-context (which should be rare).\n"
        "7.  **Be Fair:** Adjudicate actions based on common sense within the fantasy setting. Success isn't guaranteed; describe failures or partial successes logically.\n"
        "8.  **Conciseness:** Keep responses focused. Usually 1-3 paragraphs is sufficient unless describing a major event.\n\n"
        f"Remember the context of the recent conversation history provided. The current turn belongs to the player specified in the last 'user' message."
        # Add more specific rules if needed: e.g., simple combat resolution, magic system basics.
    )
    return prompt


def display_gm_response(text):
    """Formats and prints/speaks the GM's response."""
    console.print(
        Panel(
            Text(text, style="italic yellow"),
            title="[bold yellow]Game Master[/]",
            border_style="yellow",
            expand=False,
        )
    )
    speak(text, GM_VOICE_ID)


def update_history(role_or_player_name, content):
    """Adds a message to the history for LLM context."""
    if role_or_player_name == "GM":
        game_state["history"].append({"role": "assistant", "content": content})
    else:  # Player turn
        # LLM expects "user" role for player input. Content already includes name via get_llm_response call.
        game_state["history"].append(
            {"role": "user", "content": f"{role_or_player_name}: {content}"}
        )

    # Optional: More sophisticated history trimming (e.g., based on token count) could go here
    # For now, handled by slicing in get_llm_response


# --- Game Setup ---


def setup_game():
    """Gets player information and sets up the initial game state."""
    console.print(Panel("[bold magenta]Welcome to the AI-Powered Text RPG Engine![/]"))
    if tts_engine:
        speak("Welcome to the AI Powered Role Playing Game!")
    else:
        console.print("[magenta](TTS disabled or unavailable)[/]")

    if microphone is None:
        console.print("[bold yellow]Note: Microphone input is disabled. Using text input.[/]")

    num_players = 0
    while num_players < 1:
        try:
            num_input = console.input("[cyan]Enter the number of human players (1 or more): [/]")
            num_players = int(num_input)
            if num_players < 1:
                console.print("[yellow]Please enter at least 1 player.[/]")
        except ValueError:
            console.print("[red]Invalid input. Please enter a number.[/]")

    for i in range(num_players):
        player_name = ""
        while not player_name:
            player_name = console.input(f"[cyan]Enter name for Player {i + 1}: [/]").strip()
            if not player_name:
                console.print("[yellow]Player name cannot be empty.[/]")

        # Assign voices cyclically if available
        player_voice_id = None
        if PLAYER_VOICE_IDS:
            player_voice_id = PLAYER_VOICE_IDS[i % len(PLAYER_VOICE_IDS)]
        elif GM_VOICE_ID:  # Fallback to GM voice if no others
            player_voice_id = GM_VOICE_ID

        game_state["players"].append({"name": player_name, "voice_id": player_voice_id})
        voice_info = (
            f"Assigned voice ID: {player_voice_id}"
            if player_voice_id
            else "No specific voice assigned."
        )
        console.print(f"[green]Welcome, {player_name}! {voice_info}[/]")
        if tts_engine and player_voice_id:
            # Greet player with their assigned voice (or GM voice fallback)
            speak(f"Welcome, {player_name}", voice_id=player_voice_id)
        elif tts_engine:
            speak(f"Welcome, {player_name}")  # Greet with default voice

    # Initial Game Introduction from GM
    console.print("\n[bold]Generating the opening scene...[/]")
    initial_prompt_context = (
        f"The players ({', '.join([p['name'] for p in game_state['players']])}) "
        f"find themselves at '{game_state['current_location']}'. "
        f"This is the very beginning of their adventure. "
        f"Describe the scene vividly and give them a clear starting point or question to prompt their first action. "
        f"Set the mood for the world: '{game_state['world_description']}'."
    )

    # Call LLM with only the system prompt and this initial user-like instruction
    initial_messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": initial_prompt_context},
    ]

    # Use a simplified call here as history is empty
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL, messages=initial_messages, temperature=0.7, max_tokens=400
        )
        initial_gm_response = response.choices[0].message.content.strip()
    except Exception as e:
        console.print(f"[bold red]Failed to generate initial scene from LLM: {e}[/]")
        initial_gm_response = (
            f"You stand at {game_state['current_location']}. The air hums with untold possibilities. "
            "What do you do first?"
        )  # Basic fallback

    display_gm_response(initial_gm_response)
    # Add the GM's opening to history *after* displaying it
    update_history("GM", initial_gm_response)
    game_state["turn"] = 1


# --- Main Game Loop ---


def game_loop():
    """Runs the main turn-based game loop."""
    setup_game()
    if not game_state["players"]:
        console.print("[red]No players configured. Exiting.[/]")
        return

    active = True
    while active:
        current_player_data = game_state["players"][game_state["current_player_index"]]
        player_name = current_player_data["name"]

        console.print(f"\n─── Turn {game_state['turn']} | Player: [bold cyan]{player_name}[/] ───")

        player_action_text = None
        retry_attempt = 0
        max_retries = 2  # Max retries for failed speech input before forcing text

        while player_action_text is None and retry_attempt <= max_retries:
            action_result = listen_to_mic(player_name)

            if action_result == "quit":
                active = False  # Signal to exit the main loop
                player_action_text = "quit"  # Set to prevent further processing this turn
                break  # Exit the inner while loop

            elif action_result is None:
                # This means listen_to_mic failed (timeout, error, couldn't understand)
                retry_attempt += 1
                if microphone is not None:  # Only offer retry/type if mic is supposed to be working
                    if retry_attempt <= max_retries:
                        console.print(f"[yellow]Attempt {retry_attempt}/{max_retries}.[/]")
                        retry_choice = console.input(
                            "[yellow]Speech failed. Retry listening? (y/n) or type 't' to type action: [/]"
                        ).lower()
                        if retry_choice == "n":
                            player_action_text = "quit"  # Treat 'n' as wanting to quit
                            active = False
                            break
                        elif retry_choice == "t":
                            # Force text input for this turn
                            console.print("[cyan](Text Input Mode)")
                            action = input(f"{player_name} [Type Action]> ").strip()
                            if action.lower() in ["quit", "exit", "stop game", "quit game"]:
                                player_action_text = "quit"
                                active = False
                            else:
                                player_action_text = action  # Got text input, break inner loop
                            break
                        else:
                            continue  # Loop again to retry listening ('y' or anything else)
                    else:
                        console.print(
                            "[yellow]Max retries reached for speech input. Please type your action.[/]"
                        )
                        console.print("[cyan](Text Input Mode)")
                        action = input(f"{player_name} [Type Action]> ").strip()
                        if action.lower() in ["quit", "exit", "stop game", "quit game"]:
                            player_action_text = "quit"
                            active = False
                        else:
                            player_action_text = action  # Got text input, break inner loop
                        break
                else:
                    # If microphone is None, listen_to_mic should have already returned text or 'quit'
                    # This path shouldn't normally be reached if microphone is None. Handle defensively.
                    console.print(
                        "[red]Internal error: Received None from listen_to_mic unexpectedly.[/]"
                    )
                    player_action_text = "wait"  # Default action on unexpected error
                    break

            else:
                # Successfully got action text (from speech or forced text input)
                player_action_text = action_result
                break  # Exit the inner while loop

        # --- End of Input Loop ---

        if not active or player_action_text == "quit":
            break  # Exit the main game loop if quit signal received

        if not player_action_text:
            console.print("[yellow]No action provided. Skipping turn (or handle appropriately).[/]")
            # Decide if skipping turn is ok or if player *must* act
            player_action_text = "do nothing and observe"  # Give LLM something minimal

        # --- Process Valid Action ---
        # Update history *before* calling LLM
        # Note: The player name is added to the content string for the LLM call itself
        update_history(player_name, player_action_text)

        # Get GM Response based on action and history
        gm_response = get_llm_response(game_state["history"], player_action_text, player_name)

        # Display and speak GM response
        display_gm_response(gm_response)

        # Update history with GM response *after* displaying
        update_history("GM", gm_response)

        # --- TODO: State Parsing (Advanced) ---
        # Future enhancement: Analyze gm_response here to update structured game_state
        # like game_state['current_location'], inventory, quest status, etc.
        # This is complex NLP and often requires specific LLM prompting or regex.
        # Example placeholder:
        # if "you arrive at" in gm_response.lower():
        #     # ... try to parse new location ...
        #     pass

        # Advance turn to the next player
        game_state["current_player_index"] = (game_state["current_player_index"] + 1) % len(
            game_state["players"]
        )
        # Increment turn number only after a full round of players
        if game_state["current_player_index"] == 0:
            game_state["turn"] += 1

    # --- End of Game Loop ---
    console.print("[bold magenta]Exiting game.[/]")
    if tts_engine:
        speak("Goodbye!")


if __name__ == "__main__":
    try:
        game_loop()
    except KeyboardInterrupt:
        console.print("\n[bold red]Game interrupted by user (Ctrl+C). Exiting.[/]")
    except Exception:
        console.print(
            "\n[bold red]An unexpected critical error occurred in the main execution:[/]"
        )
        # Print detailed traceback for debugging
        console.print(traceback.format_exc())
    finally:
        # Attempt graceful cleanup (TTS engine might hang sometimes)
        if tts_engine:
            try:
                # This might not always work perfectly depending on the TTS engine state
                tts_engine.stop()
            except RuntimeError as e:
                if "run loop already stopped" not in str(e).lower():
                    console.print(f"[yellow]Note: Error stopping TTS engine: {e}[/]")
            except Exception as e:
                console.print(f"[yellow]Note: Non-runtime error stopping TTS engine: {e}[/]")

        console.print("[magenta]Game session ended.[/]")
