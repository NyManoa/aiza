# Raccourcis de développement (voir README.md)
PY ?= python3
export PYTHONPATH := $(CURDIR)/backend/src

.PHONY: install pipeline api web dev test lint build docker deploy-check vercel vercel-prod netlify netlify-prod

install:            ## dépendances backend (dev) + frontend
	$(PY) -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci

pipeline:           ## reconstruire backend/data/processed
	cd backend && $(PY) -m planner.pipeline

api:                ## API FastAPI en rechargement automatique (port 8000)
	cd backend && $(PY) -m uvicorn planner.api.app:app --reload --port 8000

web:                ## frontend Vite (port 5173, /api relayé vers 8000)
	cd frontend && npm run dev

test:               ## tests backend + frontend
	cd backend && $(PY) -m pytest -q
	cd frontend && npm run typecheck && npm test

lint:
	cd backend && ruff check src tests

build:              ## build de production du frontend
	cd frontend && npm run build

docker:             ## construire et lancer la pile complète (http://localhost:8080)
	docker compose up --build

deploy-check:       ## vérifications avant déploiement : données à jour, tests, build
	$(MAKE) pipeline test build

vercel:             ## déploiement de prévisualisation sur Vercel (site + API)
	$(MAKE) deploy-check
	npx vercel deploy

vercel-prod:        ## déploiement de production sur Vercel
	$(MAKE) deploy-check
	npx vercel deploy --prod

netlify:            ## déploiement de prévisualisation du site sur Netlify (API sur Render, voir netlify.toml)
	npx netlify deploy --build

netlify-prod:       ## déploiement de production du site sur Netlify
	npx netlify deploy --build --prod
