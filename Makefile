.PHONY: test-backend test-frontend test-extension test-e2e test-all

test-backend:
	cd backend && pip install pytest-cov && python -m pytest tests/ -v --cov=app --cov-report=term-missing

test-frontend:
	cd frontend && npm run test

test-extension:
	cd extension && npm run test

test-e2e:
	docker compose -f docker-compose.test.yml up --build -d
	cd extension && npx playwright test tests/e2e.spec.ts || (docker compose -f docker-compose.test.yml down && exit 1)
	docker compose -f docker-compose.test.yml down

test-all: test-backend test-frontend test-extension test-e2e
