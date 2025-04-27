#!/usr/bin/env sh

set -e

docker compose -f docker-compose.yml --env-file .env.shared --env-file .env.override exec -it -u devuser dev zsh