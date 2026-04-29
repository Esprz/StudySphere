VENV_PYTHON := /home/sy/projects/personal/StudySphere/data_simulator/.venv/bin/python
SIM_ROOT := /home/sy/projects/personal/StudySphere/data_simulator
SIM_PY := PYTHONPATH=src $(VENV_PYTHON)

# Start all services (build and run in background)
up:
	docker compose up --build -d

# Stop all running containers (without removing data)
stop:
	docker compose stop

# Stop and remove all containers (but keep volumes)
down:
	docker compose down

# Completely remove all containers and volumes (fresh reset)
reset:
	docker compose down -v

# First-time setup: start services, create initial migration, and run backend
first-run: up
	docker compose exec backend npx prisma migrate dev --name init
	docker compose exec backend npm run dev

# Normal run after first time: start backend
run: up
	docker compose exec backend npm run dev

# Normal run after first time: apply any new migrations and start backend
migrate-run: up
	docker compose exec backend npx prisma migrate dev
	docker compose exec backend npm run dev

# View logs from all services
logs:
	docker compose logs -f

# View logs from individual services
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-db:
	docker compose logs -f db

logs-etl:
	docker compose logs -f etl-service

logs-kafka:
	docker compose logs -f kafka

logs-offline:
	docker compose --profile offline logs -f offline-pipeline

logs-simulator:
	docker compose --profile offline logs -f data-simulator

# Optional: open Prisma Studio (GUI for DB)
studio:
	docker compose exec backend npx prisma studio

# Optional: check Prisma migration status
prisma-status:
	docker compose exec backend npx prisma migrate status

# Optional: run seed script if defined
prisma-seed:
	docker compose exec backend npx prisma db seed

offline-health:
	docker compose --profile offline run --rm offline-pipeline python -m src.main healthcheck

offline-run:
	docker compose --profile offline run --rm offline-pipeline python -m src.main run-all

offline-scheduler:
	docker compose --profile offline up offline-pipeline

simulator-test:
	cd $(SIM_ROOT) && $(SIM_PY) -m unittest discover -s tests

simulator-db-adapter-export:
	python3 -m simulator_db_adapter --input-dir $(SIM_ROOT)/tmp_runs/seed_openai_batch_100u_20260423_023107

simulator-run:
	cd $(SIM_ROOT) && $(SIM_PY) -m pipeline.run \
		--seed 1001 \
		--user-count 100 \
		--timeline-ticks 30 \
		--items-per-session 12 \
		--max-candidate-pool-size 80 \
		--output-dir tmp_runs/make_structured_100u

simulator-prepare-seed:
	cd $(SIM_ROOT) && $(SIM_PY) -m pipeline.batch_cli prepare-seed \
		--seed 1001 \
		--user-count 100 \
		--timeline-ticks 30 \
		--items-per-session 12 \
		--max-candidate-pool-size 80 \
		--seed-post-target-count 12 \
		--seed-comment-target-count 12 \
		--output-dir tmp_runs/make_seed_prepare_100u

simulator-prepare-scale:
	cd $(SIM_ROOT) && $(SIM_PY) -m pipeline.batch_cli prepare-scale \
		--seed 1001 \
		--user-count 1000 \
		--timeline-ticks 30 \
		--items-per-session 12 \
		--max-candidate-pool-size 80 \
		--scale-openai-model-name gpt-5-nano \
		--scale-gemini-model-name gemini-2.5-flash-lite \
		--scale-gemini-share-percentage 20 \
		--output-dir tmp_runs/make_scale_prepare_1000u

simulator-docker-run:
	docker compose --profile offline run --rm data-simulator

simulator-docker-prepare-seed:
	docker compose --profile offline run --rm data-simulator \
		python -m pipeline.batch_cli prepare-seed \
		--seed 1001 \
		--user-count 100 \
		--timeline-ticks 30 \
		--items-per-session 12 \
		--max-candidate-pool-size 80 \
		--seed-post-target-count 12 \
		--seed-comment-target-count 12 \
		--output-dir /app/output/docker_seed_prepare_100u

simulator-docker-prepare-scale:
	docker compose --profile offline run --rm data-simulator \
		python -m pipeline.batch_cli prepare-scale \
		--seed 1001 \
		--user-count 1000 \
		--timeline-ticks 30 \
		--items-per-session 12 \
		--max-candidate-pool-size 80 \
		--scale-openai-model-name gpt-5-nano \
		--scale-gemini-model-name gemini-2.5-flash-lite \
		--scale-gemini-share-percentage 20 \
		--output-dir /app/output/docker_scale_prepare_1000u
