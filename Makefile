.PHONY: help dev dev-backend dev-frontend stop clean logs install install-dev docker-up docker-down docker-logs docker-restart health test

# Chargement des variables d'environnement
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Configuration
PYTHON := python3
VENV := .venv
BACKEND_PORT := 8000
FRONTEND_PORT := 3000

# Couleurs pour l'affichage
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Afficher l'aide
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  LightOn Workflow Builder - Commandes disponibles$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Développement Local:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v "Docker" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@grep -E '^docker-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Variables d'environnement requises:$(NC)"
	@echo "  ANTHROPIC_API_KEY   : Clé API Anthropic Claude"
	@echo "  LIGHTON_API_KEY     : Clé API LightOn Paradigm"
	@echo ""

install: ## Installer les dépendances Python
	@echo "$(GREEN)[1/3] Création de l'environnement virtuel...$(NC)"
	@$(PYTHON) -m venv $(VENV) || python -m venv $(VENV)
	@echo "$(GREEN)[2/3] Mise à jour de pip...$(NC)"
	@$(VENV)/bin/pip install --upgrade pip
	@echo "$(GREEN)[3/3] Installation des dépendances...$(NC)"
	@$(VENV)/bin/pip install -r requirements.txt
	@echo "$(GREEN)✓ Installation terminée$(NC)"

install-dev: install ## Installer les dépendances de développement
	@echo "$(YELLOW)Installation des dépendances de développement...$(NC)"
	@$(VENV)/bin/pip install pytest pytest-asyncio pytest-cov httpx
	@echo "$(GREEN)✓ Dépendances de développement installées$(NC)"

verify-env: ## Vérifier les variables d'environnement
	@echo "$(YELLOW)Vérification des variables d'environnement...$(NC)"
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "$(RED)✗ ANTHROPIC_API_KEY non définie$(NC)"; \
		echo "$(YELLOW)  Ajouter dans .env : ANTHROPIC_API_KEY=your_key$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ ANTHROPIC_API_KEY définie$(NC)"; \
	fi
	@if [ -z "$$LIGHTON_API_KEY" ]; then \
		echo "$(RED)✗ LIGHTON_API_KEY non définie$(NC)"; \
		echo "$(YELLOW)  Ajouter dans .env : LIGHTON_API_KEY=your_key$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ LIGHTON_API_KEY définie$(NC)"; \
	fi
	@echo "$(GREEN)✓ Configuration OK$(NC)"

stop: ## Arrêter tous les serveurs Python locaux
	@echo "$(YELLOW)Arrêt des serveurs Python...$(NC)"
	@pkill -f "uvicorn" 2>/dev/null || true
	@pkill -f "http.server $(FRONTEND_PORT)" 2>/dev/null || true
	@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	@lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || true
	@echo "$(GREEN)✓ Serveurs arrêtés$(NC)"

dev-backend: stop ## Démarrer uniquement le backend (port 8000)
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Démarrage du backend API (port $(BACKEND_PORT))$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Environnement virtuel non trouvé. Lancer: make install$(NC)"; \
		exit 1; \
	fi
	@. $(VENV)/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

dev-frontend: ## Démarrer uniquement le frontend (port 3000)
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Démarrage du frontend (port $(FRONTEND_PORT))$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@$(PYTHON) -m http.server $(FRONTEND_PORT)

dev: stop verify-env ## Démarrer l'application complète en mode développement
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  MODE DÉVELOPPEMENT (Python local)$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Installation des dépendances...$(NC)"; \
		$(MAKE) install; \
	fi
	@echo "$(GREEN)[1/2] Démarrage du backend API (port $(BACKEND_PORT))...$(NC)"
	@. $(VENV)/bin/activate && nohup uvicorn api.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) > backend.log 2>&1 &
	@sleep 3
	@echo "$(GREEN)[2/2] Démarrage du frontend (port $(FRONTEND_PORT))...$(NC)"
	@nohup $(PYTHON) -m http.server $(FRONTEND_PORT) > frontend.log 2>&1 &
	@sleep 2
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  ✓ SERVEURS DÉMARRÉS EN MODE DEV$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "  $(BLUE)Frontend:$(NC)     http://localhost:$(FRONTEND_PORT)"
	@echo "  $(BLUE)Backend API:$(NC)  http://localhost:$(BACKEND_PORT)"
	@echo "  $(BLUE)API Docs:$(NC)     http://localhost:$(BACKEND_PORT)/docs"
	@echo ""
	@echo "$(YELLOW)Logs:$(NC)"
	@echo "  Backend:  tail -f backend.log"
	@echo "  Frontend: tail -f frontend.log"
	@echo ""
	@echo "$(YELLOW)Arrêter:$(NC) make stop"
	@echo ""

health: ## Vérifier la santé de l'API
	@echo "$(YELLOW)Vérification de l'API...$(NC)"
	@curl -s http://localhost:$(BACKEND_PORT)/health | python3 -m json.tool || echo "$(RED)✗ API non disponible$(NC)"

logs: ## Afficher les logs en temps réel
	@echo "$(YELLOW)Logs backend et frontend (CTRL+C pour arrêter)...$(NC)"
	@tail -f backend.log frontend.log 2>/dev/null || echo "$(RED)Aucun log trouvé. Serveurs démarrés ?$(NC)"

test: ## Lancer les tests
	@echo "$(YELLOW)Lancement des tests...$(NC)"
	@cd tests && make test

clean: stop ## Nettoyer les fichiers temporaires
	@echo "$(YELLOW)Nettoyage...$(NC)"
	@rm -f backend.log frontend.log
	@rm -rf __pycache__ .pytest_cache htmlcov .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

clean-all: clean ## Nettoyer tout (y compris venv)
	@echo "$(YELLOW)Suppression de l'environnement virtuel...$(NC)"
	@rm -rf $(VENV)
	@echo "$(GREEN)✓ Nettoyage complet terminé$(NC)"

# ═══════════════════════════════════════════════════════════
# Commandes Docker
# ═══════════════════════════════════════════════════════════

docker-build: ## Construire l'image Docker
	@echo "$(BLUE)Construction de l'image Docker...$(NC)"
	@docker-compose build

docker-up: ## Démarrer l'application avec Docker
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Démarrage avec Docker Compose$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@docker-compose up -d
	@sleep 3
	@echo ""
	@echo "$(GREEN)✓ Application démarrée$(NC)"
	@echo ""
	@echo "  $(BLUE)Frontend:$(NC)     http://localhost:$(FRONTEND_PORT)"
	@echo "  $(BLUE)Backend API:$(NC)  http://localhost:$(BACKEND_PORT)"
	@echo "  $(BLUE)API Docs:$(NC)     http://localhost:$(BACKEND_PORT)/docs"
	@echo ""
	@echo "$(YELLOW)Logs:$(NC) make docker-logs"
	@echo "$(YELLOW)Arrêter:$(NC) make docker-down"
	@echo ""

docker-down: ## Arrêter et supprimer les conteneurs Docker
	@echo "$(YELLOW)Arrêt des conteneurs Docker...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✓ Conteneurs arrêtés$(NC)"

docker-restart: ## Redémarrer les conteneurs Docker
	@echo "$(YELLOW)Redémarrage des conteneurs...$(NC)"
	@docker-compose restart
	@echo "$(GREEN)✓ Conteneurs redémarrés$(NC)"

docker-logs: ## Afficher les logs Docker
	@docker-compose logs -f

docker-ps: ## Afficher les conteneurs en cours d'exécution
	@docker-compose ps

docker-shell: ## Ouvrir un shell dans le conteneur
	@docker-compose exec workflow-generator /bin/bash

docker-clean: ## Nettoyer les conteneurs et images Docker
	@echo "$(YELLOW)Nettoyage Docker...$(NC)"
	@docker-compose down -v --rmi local
	@echo "$(GREEN)✓ Nettoyage Docker terminé$(NC)"

# ═══════════════════════════════════════════════════════════
# Utilitaires
# ═══════════════════════════════════════════════════════════

test-ask-question: ## Tester l'API ask_question de Paradigm
	@echo "$(YELLOW)Test de l'API ask_question de Paradigm...$(NC)"
	@if [ -z "$$LIGHTON_API_KEY" ] && [ -z "$$PARADIGM_API_KEY" ]; then \
		echo "$(RED)✗ LIGHTON_API_KEY ou PARADIGM_API_KEY non définie$(NC)"; \
		echo "$(YELLOW)  Ajouter dans .env : PARADIGM_API_KEY=your_key$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(BLUE)Entrez l'ID du fichier à tester (ex: 104039):$(NC) "; \
	read FILE_ID; \
	if [ -z "$$FILE_ID" ]; then \
		echo "$(RED)✗ ID fichier requis$(NC)"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "$(YELLOW)Envoi de la requête à Paradigm...$(NC)"; \
	API_KEY=$${PARADIGM_API_KEY:-$$LIGHTON_API_KEY}; \
	RESPONSE=$$(curl -s -w "\n%{http_code}" -X POST \
		"https://paradigm.lighton.ai/api/v2/files/$$FILE_ID/ask-question" \
		-H "Authorization: Bearer $$API_KEY" \
		-H "Content-Type: application/json" \
		-d '{"question": "Quel est le nom complet ?"}'); \
	HTTP_CODE=$$(echo "$$RESPONSE" | tail -n1); \
	BODY=$$(echo "$$RESPONSE" | sed '$$d'); \
	echo ""; \
	if [ "$$HTTP_CODE" = "200" ]; then \
		echo "$(GREEN)✓ Succès (HTTP $$HTTP_CODE)$(NC)"; \
		echo ""; \
		echo "$(BLUE)Réponse:$(NC)"; \
		echo "$$BODY" | python3 -m json.tool 2>/dev/null || echo "$$BODY"; \
	else \
		echo "$(RED)✗ Échec (HTTP $$HTTP_CODE)$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Réponse:$(NC)"; \
		echo "$$BODY"; \
	fi

test-workflow-v4: ## Tester génération workflow UGAP DC4 V4
	@echo "$(YELLOW)Test génération workflow UGAP DC4 V4...$(NC)"
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "$(RED)✗ ANTHROPIC_API_KEY non définie$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f "workflow_ugap_description_v4.txt" ]; then \
		echo "$(RED)✗ Fichier workflow_ugap_description_v4.txt introuvable$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(BLUE)Lecture de la description V4...$(NC)"
	@DESCRIPTION=$$(python3 -c "import json; print(json.dumps(open('workflow_ugap_description_v4.txt').read()))"); \
	echo ""; \
	echo "$(YELLOW)Envoi à l'API Workflow Builder...$(NC)"; \
	RESPONSE=$$(curl -s -w "\n%{http_code}" -X POST \
		"http://localhost:8000/api/workflows" \
		-H "Content-Type: application/json" \
		-d "{\"description\": $$DESCRIPTION, \"name\": \"UGAP DC4 V4 Test\"}"); \
	HTTP_CODE=$$(echo "$$RESPONSE" | tail -n1); \
	BODY=$$(echo "$$RESPONSE" | sed '$$d'); \
	echo ""; \
	if [ "$$HTTP_CODE" = "200" ] || [ "$$HTTP_CODE" = "201" ]; then \
		echo "$(GREEN)✓ Génération réussie (HTTP $$HTTP_CODE)$(NC)"; \
		echo ""; \
		WORKFLOW_ID=$$(echo "$$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', 'N/A'))"); \
		echo "$(BLUE)Workflow ID: $$WORKFLOW_ID$(NC)"; \
		echo ""; \
		CODE=$$(echo "$$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('generated_code', ''))"); \
		if echo "$$CODE" | grep -q "ask_question"; then \
			echo "$(RED)❌ ERREUR: Le code généré utilise ask_question()$(NC)"; \
		else \
			echo "$(GREEN)✓ Code correct: n'utilise pas ask_question()$(NC)"; \
		fi; \
		echo ""; \
		APIS=$$(echo "$$CODE" | grep -o "paradigm_client\.[a-z_]*(" | sort | uniq); \
		echo "$(BLUE)APIs Paradigm utilisées:$(NC)"; \
		echo "$$APIS" | sed 's/^/  - /'; \
		echo ""; \
		LINE_COUNT=$$(echo "$$CODE" | wc -l); \
		echo "$(BLUE)Taille du code: $$LINE_COUNT lignes$(NC)"; \
	else \
		echo "$(RED)✗ Échec (HTTP $$HTTP_CODE)$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Réponse:$(NC)"; \
		echo "$$BODY" | python3 -m json.tool 2>/dev/null || echo "$$BODY"; \
	fi

format: ## Formater le code Python (black)
	@if [ -d "$(VENV)" ]; then \
		echo "$(YELLOW)Formatage du code...$(NC)"; \
		$(VENV)/bin/black api/ tests/ 2>/dev/null || echo "$(YELLOW)black non installé$(NC)"; \
	else \
		echo "$(RED)Environnement virtuel non trouvé$(NC)"; \
	fi

lint: ## Linter le code Python (flake8)
	@if [ -d "$(VENV)" ]; then \
		echo "$(YELLOW)Linting du code...$(NC)"; \
		$(VENV)/bin/flake8 api/ tests/ 2>/dev/null || echo "$(YELLOW)flake8 non installé$(NC)"; \
	else \
		echo "$(RED)Environnement virtuel non trouvé$(NC)"; \
	fi

.DEFAULT_GOAL := help
