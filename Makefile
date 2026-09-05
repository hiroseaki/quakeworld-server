.PHONY: setup build up down logs smoke check

setup:
	@test -f .env || cp .env.example .env
	@test -f .secrets/rcon_password || (umask 077 && openssl rand -base64 32 > .secrets/rcon_password)
	@echo "Add pak0.pak (and preferably pak1.pak) to data/id1/, then run: make up"

build:
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f server

smoke:
	./scripts/smoke-test.sh

check:
	./scripts/check.sh
