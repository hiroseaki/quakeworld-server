.PHONY: setup build up down logs smoke check
setup:
	@test -f .env || (umask 077 && cp .env.example .env)
	@mkdir -p pak_files data/maps data/locs .secrets
	@echo "Edit .env, add pak0.pak and pak1.pak to pak_files/, then run make up."
build:
	docker compose --profile '*' build
up:
	docker compose up -d --build
down:
	docker compose --profile '*' down
logs:
	docker compose logs -f
smoke:
	./scripts/smoke-test.sh
check:
	./scripts/check.sh
