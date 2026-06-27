COMPOSE_FILE ?= infra/docker-compose.yml
ENV_FILE := $(if $(wildcard .env),.env,.env.example)
COMPOSE_PARALLEL_LIMIT ?= 1
KIND_CLUSTER ?= risk-platform
K8S_NAMESPACE ?= risk-platform
BANKING_CORE_BUILD_DIR ?= $(TEMP)/banking-core-build
AUTH_SERVICE_BUILD_DIR ?= $(TEMP)/auth-service-build
GRADLE_USER_HOME ?= $(TEMP)/banking-core-gradle-home
export COMPOSE_PARALLEL_LIMIT
export BANKING_CORE_BUILD_DIR
export AUTH_SERVICE_BUILD_DIR
export GRADLE_USER_HOME

.PHONY: help docker-check up down logs ps dashboard-dev dashboard-build test-backend test-all e2e k8s-create k8s-delete k8s-build-images k8s-load-images k8s-deploy k8s-status k8s-logs
help:
	@echo "Real-time Transaction Fraud Detection Platform"
	@echo "make up    - start local infrastructure"
	@echo "make down  - stop local infrastructure"
	@echo "make logs  - follow local infrastructure logs"
	@echo "make ps    - show local infrastructure status"
	@echo "make dashboard-dev   - run local frontend dashboard"
	@echo "make dashboard-build - build frontend dashboard"
	@echo "make test-backend - run banking-core backend tests"
	@echo "make test-all     - run local unit tests for backend and Python pipelines"
	@echo "make e2e   - run local end-to-end fraud detection smoke test"
	@echo "make k8s-create       - create local kind cluster"
	@echo "make k8s-delete       - delete local kind cluster"
	@echo "make k8s-build-images - build stateless service images"
	@echo "make k8s-load-images  - load service images into kind"
	@echo "make k8s-deploy       - apply Kubernetes manifests"
	@echo "make k8s-status       - show Kubernetes resources"
	@echo "make k8s-logs         - show service logs"

docker-check:
	@docker info >NUL 2>NUL || (echo Docker is not running. Start Docker Desktop, wait for it to finish starting, then rerun this command. && exit 1)

up: docker-check
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d

down: docker-check
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down

logs: docker-check
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) logs -f

ps: docker-check
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) ps

dashboard-dev:
	cd services/dashboard && npm run dev

dashboard-build:
	cd services/dashboard && npm run build

test-backend:
	cd services/banking-core && gradle test --no-daemon
	cd services/auth-service && gradle test --no-daemon

test-all: test-backend
	cd services/fraud-decision-api && py -m pytest
	cd pipelines/training && py -m unittest discover -s tests
	cd pipelines/spark-streaming && py -m unittest discover -s tests

e2e:
	py tests/e2e/run_fraud_detection_flow.py

k8s-create: docker-check
	kind create cluster --name $(KIND_CLUSTER) --config infra/k8s/kind/kind-config.yaml

k8s-delete: docker-check
	kind delete cluster --name $(KIND_CLUSTER)

k8s-build-images: docker-check
	docker build -t banking-core:local services/banking-core
	docker build -t auth-service:local services/auth-service
	docker build -t fraud-decision-api:local -f services/fraud-decision-api/Dockerfile .

k8s-load-images: docker-check
	kind load docker-image banking-core:local --name $(KIND_CLUSTER)
	kind load docker-image auth-service:local --name $(KIND_CLUSTER)
	kind load docker-image fraud-decision-api:local --name $(KIND_CLUSTER)

k8s-deploy:
	kubectl apply -f infra/k8s/namespace.yaml
	kubectl apply -f infra/k8s/auth-service
	kubectl apply -f infra/k8s/fraud-decision-api
	kubectl apply -f infra/k8s/banking-core

k8s-status:
	kubectl get all -n $(K8S_NAMESPACE)

k8s-logs:
	kubectl logs -n $(K8S_NAMESPACE) deployment/auth-service --tail=100
	kubectl logs -n $(K8S_NAMESPACE) deployment/fraud-decision-api --tail=100
	kubectl logs -n $(K8S_NAMESPACE) deployment/banking-core --tail=100
