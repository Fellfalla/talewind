# talewind
AI assistant for pen&amp;paper

## Prerequisites
1. Setup ollama via `. ./setup/ollama.sh`

## Launch
1. `docker compose --env-file .env.shared --env-file .env.override up`
2. `docker exec -it talewind-dev-1 /bin/zsh`
3. `pixi run talewind_app`