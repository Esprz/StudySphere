# Start all services (build and run in background)
up:
	docker compose up --build -d

# Stop all running containers (without removing data)
stop:
	docker compose stop

# Completely remove all containers and volumes (fresh reset)
reset:
	docker compose down -v

# First-time setup: start services, create initial migration, and run backend in background
first-run: up
	docker compose exec backend npx prisma migrate dev --name init
	docker compose exec backend npm run dev

# Normal run after first time: apply any new migrations and start backend in background
run: up
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

# Optional: open Prisma Studio (GUI for DB)
studio:
	docker compose exec backend npx prisma studio

# Optional: check Prisma migration status
status:
	docker compose exec backend npx prisma migrate status

# Optional: run seed script if defined
seed:
	docker compose exec backend npx prisma db seed
