SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ollama create game_master -f "${SCRIPT_DIR}/../ai/game_master.modelfile"
ollama run game_master