from openai import OpenAI
from pydantic import BaseModel
from typing import Final
from typing import AsyncGenerator
from .mcp_servers.mcp_facade import McpFacade
import mcp
from openai.types.responses import ToolParam, FunctionToolParam

client = OpenAI()


class MasterResponse(BaseModel):
    content: str
    voice: str


memory = []
memory_size_limit = 20  # NOTE: instead of trimming, compress the memory


def convert_tools(mcp_tools: mcp.types.ListToolsResult) -> list[ToolParam]:
    """
    Convert mcp tools to OpenAI tools.
    """
    return [
        FunctionToolParam(
            name=mcp_tool.name,
            parameters=mcp_tool.inputSchema,
            description=mcp_tool.description,
            type="function",
        )
        for mcp_tool in mcp_tools.tools
    ]


class Agent:
    DEFAULT_LLM_MODEL: Final = "o4-mini"  # Or "gpt-3.5-turbo" or other compatible models
    DEFAULT_SYSTEM_PROMPT: Final = """
    Über dich: Du bist ein zynischer Spielleiter für pen and paper. Dein Charakter is geprägt von mit schwarzem Humor und du legt viel Weisheit und Tiefgang in jedes einzelne deiner Worte. Du bist erfahren, weise, mysteriös, und gezeichnet vom Leben.

    Deine Aufgabe: Führe eine Gruppe von Abenteurern durch eine Kampagne und sorge für ihre Unterhaltung. Lehne dich an das klassischen Dungeons and Dragons an, aber halte das Regelwerk simpel, z.B. ohne Attribute. Sei proaktiv und gestalte eine interessante, spannende und falls passend außergewöhnliche Welt. 

    Dein Verhalten: Vergiss nie deine zynische und mismutige Natur. Du bist unter Umständen widerwillig, aber nimmst deine jederzeit Aufgabe ernst. Passe deine Sprache, ob gehoben, Slang, erzählerisch Spannend, dichtend, mittelalterlich, ausgeschmückt, und so weiter and das gesamte Setting an.
    Halte dich kurz und prägnant, humor und eloquenz ist gern gesehen, versuch aber im großen und ganzen eine kohärentes Bild abzugeben. Zwischendurch lachst du schurkenhaft wenn du die spieler in eine missliche Lage bringst, oder sie sich selbst in eine solche bringen. Du liebst es die Spieler zu verspotten.

    Ablauf:
    1. Frage nach der Anzahl der Spieler
    2. Schlage 1 kampagnen vor und frage die Spieler ob sie diese spielen möchten
    3. Erzeuge ein anfangsszenario, in dem die charaktäre interaktiv erstellt werden
    4. Nachdem alle Charaktäre mit Stärken und schwächen erzeugt wurden, führe die Spieler in das Abenteuer
    5. Du entscheidest was passiert, Würfle für Erfolg und Miserfolg bei aktionen, sei dabei stochastisch in der Würfelverteilung.
    6. Wenn das Abenteuer zu ende ist, schreibe einen kurzen Epilog.

    Regeln:
    * Jeder Spieler hat name, hintergrund, volk, staerke, schwaeche 
    * Sorge dafür, dass die Regeln immer möglichst konsequent eingehalten werden und verhindere Aktionen der Spieler, bei der sie ihre Rolle verlassen.
    * Kriere proaktiv eine bemerkenswerte Geschichte
    * Bei Unklarheit ist deine Proaktivität gefragt. Es ist zu jedem Zeitpunkt verboten die Spieler danach zu fragen, was als nächstes passiert. Das ist deine Aufgabe als spielleiter Schleifen und Sackgassen nach gewisser Zeit mit kreativen Optionen zu lösen.
    * Sorge dafür dass alle spieler regelmäßig an die Reihe kommen, indem du bei Sie langer Inaktivität explizit zur Aktion aufforderst.

    """
    # Beschreibe den Stil deiner stimme, z.b: freundlich, aufgeregt, schreiend, kreischend, spannend, mysterioes, flüstern, laut, leise, schockiert, und so weiter.

    # Strong voice with a touch of black mockery. Mysterious and tensing way of speaking, high variance in pitch. Rolling R like a pirate.
    VOICE_DEFAULT = """
    Tone: Dark voice, Mysterious and mocking. High variance in pitch.

    Pacing: Normal. Building excitement, deliberate, pausing slightly after suspenseful moments to heighten drama.

    Emotion: Engaging and determined.

    Emphasis: Highlight dark humor, vocals, names, and actions.

    Pronunciation: Very literal pronunciation with very strong rolling every single R in each word.
    """

    def __init__(self, system_prompt: str, mcp_facade: McpFacade | None):
        self._mcp_facade = mcp_facade
        self._system_prompt = system_prompt

    async def create_response(self, request: str) -> AsyncGenerator[MasterResponse, None]:
        global memory
        memory.append({"role": "user", "content": request})

        # Limit memory size
        if len(memory) > memory_size_limit:
            memory = memory[-memory_size_limit:]

        if self._mcp_facade is None:
            tools = []
        else:
            tools = convert_tools(await self._mcp_facade.list_tools())

        stream = client.responses.create(
            model=self.DEFAULT_LLM_MODEL,
            input=[
                {"role": "system", "content": self._system_prompt},
                *memory,
            ],
            tools=tools,
            stream=True,
        )

        full_answer = ""
        buffer = ""
        mode = "immediate"  # or "buffered"
        if mode == "immediate":
            for event in stream:
                if hasattr(event, "type") and "text.delta" in event.type:
                    full_answer += event.delta
                    yield MasterResponse(content=event.delta, voice=self.VOICE_DEFAULT)
        elif mode == "buffered":
            for event in stream:
                if hasattr(event, "response") and hasattr(event.response, "output_text"):
                    buffer += event.response.output_text
                    while "." in buffer:
                        sentence, buffer = buffer.split(".", 1)
                    full_answer += sentence.strip() + ". "
                    yield MasterResponse(content=sentence.strip() + ". ", voice=self.VOICE_DEFAULT)
        else:
            raise ValueError("Invalid mode. Use 'immediate' or 'buffered'.")

        # Yield any remaining text in the buffer as the final sentence
        if buffer:
            full_answer += buffer.strip()
            yield MasterResponse(content=buffer.strip(), voice=self.VOICE_DEFAULT)

        # Update memory
        memory.append({"role": "assistant", "content": full_answer})
