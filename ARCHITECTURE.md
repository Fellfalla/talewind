# ARCHITECTURE.md — Implementation Reference

Technical details for the AI-narrated RPG game master web app. For agent guidelines and rules, see [AGENTS.md](AGENTS.md).

---

## Project Structure

```
index.html       <- THE ENTIRE APP. Single file. React + JSX + styles + game logic. SOURCE OF TRUTH.
manifest.json    <- PWA metadata (name, icons, display mode)
sw.js            <- Service worker for offline caching. Bump CACHE_NAME on every deploy.
icon-*.png       <- App icons (192px, 512px)
.nojekyll        <- GitHub Pages bypass
```

### Single Source of Truth: `index.html`

There is no separate JSX source file, no build step, no bundler. All changes happen directly in `index.html`. The file is ~1360 lines and self-contained: HTML boilerplate, CDN imports (React 18, ReactDOM, Babel), a localStorage shim (`_store`), and a single `<script type="text/babel">` block containing all game logic and UI.

If a `rpg-game-master.jsx` artifact exists elsewhere, it is **stale and behind** `index.html`. Do not treat it as canonical.

### Key Sections in index.html (marked with `// ─── Section ───` comments)

- **Constants** (~line 39): `SCENARIOS`, `CLASSES`, `RACES`, `STARTER_ITEMS`, `SKILL_TREES`, `NARRATOR_TYPES` — game content data
- **Dice Engine** (~line 137): `rollDie`, `rollDice`, `rollStat` — 4d6-drop-lowest stat generation
- **Voice Engine** (~line 146): Browser SpeechRecognition + SpeechSynthesis, Kokoro TTS (in-browser via WASM/WebGPU)
- **Main App** (~line 203): All state, persistence (localStorage via `_store`), API calls, game logic, and rendering
- **AI Narrator** (~line 499): System prompt construction (`narratorPrompt`) and Anthropic API call (`callNarrator`)
- **Styles** (~line 1286): All inline style definitions in the `st` object

### Development

No build commands. Open `index.html` in a browser or serve with any static file server:

```
python3 -m http.server 8000
# or
npx serve .
```

---

## App Phases

```
loading -> setup -> character -> playing
                 ^                  |
                 +--- (new game) ---+
```

- **loading**: Reads autosave from storage. If found, restores phase. Otherwise -> setup.
- **setup**: Scenario selection, narrator selection, parameters, player count. Saved games shown inline.
- **character**: Sequential character creation (1 per player). Name -> Race -> Class -> Backstory -> Stats -> Confirm.
- **playing**: Split-panel UI. Story log + input on left, dice + stats on right. Side panel restructured on mobile <700px.

---

## State Variables (~36 total)

**Core game state** (persisted in autosave):
- `phase` — "loading" | "setup" | "character" | "playing"
- `scenario` — scenario ID string (e.g., "dark_fantasy")
- `strictness` — 1-10 int, `antiCheat` — 1-10 int
- `characters` — array of character objects (see schema below)
- `activeChar` — index into characters[]
- `storyLog` — array of `{ type: "narrator"|"player"|"roll", text: string, character?: string }`

**Voice/TTS**: `voiceEnabled`, `isListening`, `isSpeaking`, `interimText`, `kokoroVoice`, `kokoroModelId`, `kokoroLoading`

**Refs**: `recognitionRef` (SpeechRecognition), `storyEndRef` (scroll anchor), `audioRef` (current TTS audio), `ttsAbortRef` (AbortController for in-flight TTS), `kokoroRef` (loaded KokoroTTS instance)

### Character Object Schema
```js
{
  id: "1679...",          // Date.now() string
  name: "Grunk",
  race: "Orc",
  class: "Warrior",
  stats: { STR: 16, DEX: 12, CON: 14, INT: 8, WIS: 10, CHA: 7 },
  hp: 14, maxHp: 14,
  inventory: ["Iron Sword", "Chain Mail", "Healing Potion"],
  skills: ["Heavy Strike", "Shield Bash", "Battle Cry"],
  backstory: "A former gladiator...",
  xp: 0, level: 1,
  conditions: []           // Unused currently. Intended for status effects.
}
```

### Storage Keys
| Key | Content |
|---|---|
| `rpg-autosave` | Full game state JSON |
| `rpg-save-slot-1` ... `rpg-save-slot-5` | Manual save state JSON + metadata |
| `rpg-anthropic-key` | Anthropic API key string |
| `rpg-kokoro-voice` | Selected Kokoro voice ID string (default: "am_adam") |
| `rpg-kokoro-model` | Selected Kokoro model preset ID (default: "q8_wasm") |

---

## Data Constants — How to Add Content

### Adding a Scenario

You must add an entry in ALL 5 maps. Use an existing scenario as template:

```js
// 1. SCENARIOS[] — add object
{ id: "my_scenario", name: "My Scenario", icon: "X",
  desc: "Short tagline for the card.",
  setting: "Long description for the AI system prompt. Describe the world, tone, what HP represents, what 'combat' means." }

// 2. CLASSES.my_scenario — exactly 6 classes
my_scenario: ["Class1", "Class2", "Class3", "Class4", "Class5", "Class6"],

// 3. RACES.my_scenario — exactly 6 races/backgrounds
my_scenario: ["Race1", "Race2", "Race3", "Race4", "Race5", "Race6"],

// 4. STARTER_ITEMS.my_scenario — 3 items per class
my_scenario: { Class1: ["Item A", "Item B", "Item C"], Class2: [...], ... },

// 5. SKILL_TREES.my_scenario — 3 skills per class
my_scenario: { Class1: ["Skill A", "Skill B", "Skill C"], Class2: [...], ... },
```

### Adding a Narrator Type

Add to `NARRATOR_TYPES[]`:
```js
{ id: "unique_id", name: "Display Name", icon: "X",
  desc: "Short description for the selection card.",
  // voiceDesc removed — voice selection is now done via Kokoro voice picker in Settings
  personality: "System prompt personality. See narrator rules in AGENTS.md." }
```

---

## AI Narrator System

### System Prompt Construction (`narratorPrompt()`)

Assembled from: narrator personality, scenario setting, strictness parameters, full character summaries (stats/HP/inventory/skills/backstory), voice acting rules, game rules, and (in multiplayer) a CURRENT TURN directive.

### Conversation History

`callNarrator(messages)` sends the last 20 story log entries as alternating user/assistant messages.

### Response Tag Parsing (`processNarratorResponse()`)

Centralized function that handles ALL narrator responses (both opening narration and player turns):
1. `[SFX: description]` — extracted and stripped (no audio playback; SFX generation was removed with ElevenLabs)
2. `[INVENTORY: Name +item]` / `[INVENTORY: Name -item]` — mutates character inventory
3. `[HP: Name +/-N]` — mutates character HP (clamped to 0..maxHp)
4. `[TURN: CharName]` — parsed for multiplayer turn advancement
5. All tags stripped from display text and TTS input

### Multiplayer Turn System

- Narrator ends responses with `[TURN: CharName]` to direct the story
- `nextAliveChar()` provides round-robin fallback (skips dead characters)
- Active character shown with sword emoji + "TURN" badge on tabs

---

## Voice System

### TTS Pipeline (`speakNarration()`)
```
Text -> Strip tags ([SFX:], [TURN:], [ROLL:], [INVENTORY:], [HP:])
     -> loadKokoro() (lazy-loads model on first call, ~80MB one-time download)
        -> Kokoro loaded?
           YES -> tts.generate(text, {voice, speed})
                  -> buildWavBlob(audio, sampling_rate) -> ObjectURL -> <audio>.play()
           NO  -> Browser SpeechSynthesis fallback (rate 0.85, pitch 0.6)
```

Kokoro TTS (kokoro-js) runs 100% in-browser via WASM/WebGPU. No API key required. Model is loaded from jsdelivr CDN via a `<script type="module">` tag that exposes `window.KokoroTTS`. The ONNX model (~80MB for q8) is downloaded lazily on first narration and cached by Transformers.js in IndexedDB.

User-selectable model presets: `q8_wasm` (default, ~80MB), `fp16_webgpu` (~150MB, requires WebGPU), `q4_wasm` (~40MB, lower quality). Curated voice list of 8 voices.

### Voice Input (Web Speech API)
Continuous mode with auto-restart on browser timeout (~60s). `no-speech` errors ignored. Ref cleared before `.stop()` to prevent restart loop.

---

## External API Contracts

### Anthropic Messages API
```
POST https://api.anthropic.com/v1/messages
Headers: Content-Type, x-api-key, anthropic-version: "2023-06-01",
         anthropic-dangerous-direct-browser-access: "true"
Body: { model: "claude-sonnet-4-20250514", max_tokens: 1000, system: string, messages: [...] }
```
The `anthropic-dangerous-direct-browser-access: "true"` header is REQUIRED for browser-to-API calls. Users must enable this flag when creating their API key.

---

## Common Modification Tasks

### "Change the AI model"
Search for `claude-sonnet-4-20250514` and replace. Used in `callNarrator()` and backstory generation.

### "Add XP/leveling"
`character.xp` and `character.level` already exist but are never incremented. Add a `[XP: CharName +50]` tag, parse it in `processNarratorResponse()`, add level-up logic, and update `narratorPrompt()` to instruct the AI to award XP.

### "Add combat initiative"
Add a combat phase state. When narrator sends `[COMBAT START]`, switch to turn-order mode. Roll initiative (d20 + DEX mod). Display turn order UI. Return to freeform after `[COMBAT END]`.

### "Stale service worker content"
Bump `CACHE_NAME` in `sw.js` (e.g., `rrrusty-rpg-v3`). The activate handler auto-purges old caches.

---

## Pitfalls & Gotchas

1. **Service worker caching**: Will aggressively serve old `index.html`. Always bump `CACHE_NAME`.
2. **Kokoro TTS model download**: First use downloads ~80MB (q8) model. Cached in IndexedDB by Transformers.js after first load.
3. **Anthropic CORS**: The API key must have "direct browser access" enabled. This is a per-key setting at creation time. Without it -> 403.
4. **Story context window**: Only the last 20 log entries are sent to the API. Older context is lost.
5. **Character name collisions**: The tag parser uses regex on character names. Names with regex-special characters or substring matches may break parsing.
6. **Mobile scrolling**: `body` must NOT have `overflow: hidden` — only the game container in playing phase.
7. **400 errors from Anthropic**: Usually means insufficient credits, not a code bug. The error is parsed and displayed in full.

---

## Deployment

All game logic runs client-side. The server only serves static files. No backend is needed — API calls go directly from the browser to Anthropic. TTS runs entirely in-browser via Kokoro (WASM/WebGPU).

### Option A: Self-Host on Raspberry Pi

#### With Caddy (simplest, auto-HTTPS if you have a domain)

```bash
# Install Caddy
sudo apt install -y caddy

# Copy app files
sudo mkdir -p /var/www/rpg
sudo cp index.html manifest.json sw.js icon-*.png .nojekyll /var/www/rpg/

# /etc/caddy/Caddyfile — for local network (no HTTPS):
:8080 {
    root * /var/www/rpg
    file_server
    encode gzip
    header /sw.js Cache-Control "no-cache"
}

# Or with a domain (auto-HTTPS via Let's Encrypt):
# your-domain.com {
#     root * /var/www/rpg
#     file_server
#     encode gzip
#     header /sw.js Cache-Control "no-cache"
# }

sudo systemctl restart caddy
```

#### With nginx

```bash
sudo apt install -y nginx
sudo mkdir -p /var/www/rpg
sudo cp index.html manifest.json sw.js icon-*.png .nojekyll /var/www/rpg/

sudo tee /etc/nginx/sites-available/rpg << 'CONF'
server {
    listen 80;
    server_name _;
    root /var/www/rpg;
    index index.html;

    gzip on;
    gzip_types text/html application/json application/javascript;

    location /sw.js {
        add_header Cache-Control "no-cache";
    }
    location / {
        try_files $uri $uri/ /index.html;
    }
}
CONF

sudo ln -sf /etc/nginx/sites-available/rpg /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

Access at `http://<raspberry-pi-ip>`. For external HTTPS, use Cloudflare Tunnel or Certbot.

**PWA install note:** The "Install App" prompt requires HTTPS. On local network without HTTPS, the app works in the browser but won't be installable. Use Caddy with a domain for auto-HTTPS.

#### Update script (`deploy.sh`)
```bash
#!/bin/bash
sudo cp index.html manifest.json sw.js icon-*.png /var/www/rpg/
echo "Deployed. Bump CACHE_NAME in sw.js if index.html changed."
```

### Option B: Build as Android App (TWA)

A Trusted Web Activity (TWA) wraps your hosted PWA in a native Android shell — full-screen, no browser chrome, Play Store distributable. No code changes to the app itself. Requires HTTPS hosting first.

#### Prerequisites
- Node.js 18+
- Java JDK 11+
- Your PWA hosted at an HTTPS URL with valid `manifest.json`

#### Using Bubblewrap (by Google Chrome Labs)

```bash
# 1. Install (package published by GoogleChromeLabs)
npm install -g @bubblewrap/cli

# 2. Initialize from your hosted manifest URL
bubblewrap init --manifest https://your-domain.com/manifest.json

# 3. Follow the interactive wizard (app name, package ID, signing key, colors)
#    It will download Android SDK components automatically on first run

# 4. Build the APK and AAB
bubblewrap build

# Output:
#   app-release-signed.apk   <- sideload or distribute directly
#   app-release-bundle.aab   <- upload to Google Play Store
```

#### Digital Asset Links (required for TWA verification)

For the TWA to display without a browser URL bar, you must prove you own the domain. After building, Bubblewrap outputs your signing key fingerprint.

Create `/.well-known/assetlinks.json` on your web server:
```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.yourname.rpg",
    "sha256_cert_fingerprints": ["YOUR_FINGERPRINT_FROM_BUBBLEWRAP"]
  }
}]
```

On the Raspberry Pi, add to your Caddy/nginx config:
```
# Caddy: add inside the site block
handle /.well-known/assetlinks.json {
    header Content-Type application/json
}

# nginx: add inside server block
location /.well-known/assetlinks.json {
    default_type application/json;
}
```

#### Sideloading the APK (no Play Store)

```bash
# Transfer APK to phone and install, or:
adb install app-release-signed.apk
```

Enable "Install from unknown sources" in Android settings. This is the quickest path — no Play Store account needed.

### Option C: Capacitor (alternative to TWA)

If you need deeper native Android integration (e.g., local file access, notifications), use Capacitor instead of TWA. This is heavier but gives you a real native shell.

```bash
npm install @capacitor/core @capacitor/cli
npx cap init "Rrrusty RPG" "com.yourname.rpg" --web-dir .
npx cap add android
npx cap sync
npx cap open android   # Opens in Android Studio
```

Build the APK from Android Studio. Capacitor copies your static files into a WebView-based Android app. All game logic stays client-side.

**When to use TWA vs Capacitor:**
- **TWA**: Simplest path. No code changes. Updates deploy instantly via web. Requires HTTPS hosting.
- **Capacitor**: Use if you need native APIs, offline-first without a server, or Play Store presence without hosting.
