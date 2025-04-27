from openai import OpenAI
from pydantic import BaseModel
client = OpenAI()
from typing import AsyncGenerator
LLM_MODEL = "o4-mini"  # Or "gpt-3.5-turbo" or other compatible models



SYSTEM_PROMPT = """
Über dich: Du bist ein zynischer Spielleiter für pen and paper. Dein Charakter is geprägt von mit schwarzem Humor und du legt viel Weisheit und Tiefgang in jedes einzelne deiner Worte.

Deine Aufgabe: Führe eine Gruppe von Abenteurern durch eine Kampagne und sorge für ihre Unterhaltung. Lehne dich an das klassischen Dungeons and Dragons an, aber halte das Regelwerk simpel, z.B. ohne Attribute. Sei proaktiv und gestalte eine interessante, spannende und falls passend außergewöhnliche Welt. 

Dein Verhalten: Vergiss nie deine zynische und mismutige Natur. Du bist unter Umständen widerwillig, aber nimmst deine jederzeit Aufgabe ernst. Passe deine Sprache, ob gehoben, Slang, erzählerisch Spannend, dichtend, mittelalterlich, ausgeschmückt, und so weiter and das gesamte Setting an.
Halte dich kurz und prägnant, humor und eloquenz ist gern gesehen, versuch aber im großen und ganzen eine kohärentes Bild abzugeben.

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

VOICE_DEFAULT = "strong voice, sarcastic, with a touch of black mockery. A strongly rolling r like a pirate RRRRR"

class MasterResponse(BaseModel):
    content: str
    voice: str


async def create_response(request: str) -> AsyncGenerator[MasterResponse, None]:
    stream = client.responses.create(
        model=LLM_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ],
        stream=True,
    )

    buffer = ""
    for event in stream:
        if hasattr(event, "response") and hasattr(event.response, "output_text"):
            buffer += event.response.output_text
            while '.' in buffer:
                sentence, buffer = buffer.split('.', 1)
                yield MasterResponse(content=sentence.strip() + '.', voice=VOICE_DEFAULT)

    # Yield any remaining text in the buffer as the final sentence
    if buffer:
        yield MasterResponse(content=buffer.strip(), voice=VOICE_DEFAULT)
