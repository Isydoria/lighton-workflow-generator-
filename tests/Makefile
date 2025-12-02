.PHONY: help test test-all test-workflow test-files test-paradigm test-integration test-security clean install

# Chargement des variables d'environnement
ifneq (,$(wildcard ../.env))
    include ../.env
    export
endif

# Configuration
PYTHON := python3
PYTEST := pytest
API_BASE_URL ?= http://localhost:8000
PARADIGM_BASE_URL ?= https://paradigm.lighton.ai

# Couleurs pour l'affichage
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Afficher l'aide
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Tests - LightOn Workflow Builder$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Commandes disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Variables d'environnement requises:$(NC)"
	@echo "  LIGHTON_API_KEY     : Clé API LightOn Paradigm"
	@echo "  ANTHROPIC_API_KEY   : Clé API Anthropic"
	@echo "  API_BASE_URL        : URL backend (défaut: http://localhost:8000)"
	@echo ""

install: ## Installer les dépendances de test
	@echo "$(GREEN)Installation des dépendances de test...$(NC)"
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install pytest pytest-asyncio pytest-cov httpx aiohttp requests python-dotenv
	@echo "$(GREEN)✓ Dépendances installées$(NC)"

test: install ## Lancer tous les tests
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Lancement de tous les tests$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	$(PYTEST) -v --tb=short --cov=../api --cov-report=term-missing --cov-report=html

test-all: test-paradigm test-workflow test-files test-integration ## Lancer tous les tests de manière séquentielle
	@echo "$(GREEN)✓ Tous les tests terminés$(NC)"

test-paradigm: install ## Tester les endpoints Paradigm API
	@echo "$(YELLOW)Test des endpoints Paradigm API...$(NC)"
	$(PYTEST) -v test_paradigm_api.py -k paradigm

test-workflow: install ## Tester les workflows (création, exécution)
	@echo "$(YELLOW)Test des workflows...$(NC)"
	$(PYTEST) -v test_workflow_api.py -k workflow

test-files: install ## Tester l'upload et gestion de fichiers
	@echo "$(YELLOW)Test des fichiers...$(NC)"
	$(PYTEST) -v test_files_api.py -k files

test-integration: install ## Tester les scénarios d'intégration complets
	@echo "$(YELLOW)Test d'intégration...$(NC)"
	$(PYTEST) -v test_integration.py -k integration

test-security: install ## Tester la sécurité du sandbox
	@echo "$(YELLOW)Test de sécurité...$(NC)"
	$(PYTEST) -v test_security.py -k security

test-quick: install ## Tests rapides (sans upload de fichiers)
	@echo "$(YELLOW)Tests rapides...$(NC)"
	$(PYTEST) -v -m "not slow"

test-smoke: ## Test smoke (vérification rapide que l'API répond)
	@echo "$(YELLOW)Test smoke...$(NC)"
	@curl -f $(API_BASE_URL)/health || (echo "$(RED)✗ API ne répond pas$(NC)" && exit 1)
	@echo "$(GREEN)✓ API répond correctement$(NC)"

test-coverage: install ## Générer le rapport de couverture
	@echo "$(YELLOW)Génération du rapport de couverture...$(NC)"
	$(PYTEST) --cov=../api --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Rapport disponible dans htmlcov/index.html$(NC)"

test-watch: install ## Lancer les tests en mode watch
	@echo "$(YELLOW)Mode watch activé (CTRL+C pour arrêter)...$(NC)"
	$(PYTEST) -v -f

test-failed: install ## Relancer uniquement les tests qui ont échoué
	@echo "$(YELLOW)Relancement des tests échoués...$(NC)"
	$(PYTEST) --lf -v

test-verbose: install ## Lancer les tests en mode très verbeux
	@echo "$(YELLOW)Tests en mode verbeux...$(NC)"
	$(PYTEST) -vv --tb=long

benchmark: install ## Benchmark de performance des endpoints
	@echo "$(YELLOW)Benchmark de performance...$(NC)"
	$(PYTHON) benchmark_api.py

clean: ## Nettoyer les fichiers de test
	@echo "$(YELLOW)Nettoyage des fichiers de test...$(NC)"
	rm -rf __pycache__ .pytest_cache htmlcov .coverage
	rm -rf test_uploads/*.pdf test_uploads/*.txt
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

verify-env: ## Vérifier les variables d'environnement
	@echo "$(YELLOW)Vérification des variables d'environnement...$(NC)"
	@if [ -z "$$LIGHTON_API_KEY" ]; then \
		echo "$(RED)✗ LIGHTON_API_KEY non définie$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ LIGHTON_API_KEY définie$(NC)"; \
	fi
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "$(RED)✗ ANTHROPIC_API_KEY non définie$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ ANTHROPIC_API_KEY définie$(NC)"; \
	fi
	@echo "$(GREEN)✓ Toutes les variables sont définies$(NC)"

check-api: ## Vérifier que l'API backend est démarrée
	@echo "$(YELLOW)Vérification de l'API backend...$(NC)"
	@curl -s -f $(API_BASE_URL)/health > /dev/null && \
		echo "$(GREEN)✓ API backend disponible sur $(API_BASE_URL)$(NC)" || \
		(echo "$(RED)✗ API backend non disponible. Démarrer avec: make start-api$(NC)" && exit 1)

start-api: ## Démarrer l'API backend en arrière-plan
	@echo "$(YELLOW)Démarrage de l'API backend...$(NC)"
	@cd .. && docker-compose up -d
	@echo "$(GREEN)✓ API démarrée$(NC)"
	@sleep 3
	@$(MAKE) check-api

stop-api: ## Arrêter l'API backend
	@echo "$(YELLOW)Arrêt de l'API backend...$(NC)"
	@cd .. && docker-compose down
	@echo "$(GREEN)✓ API arrêtée$(NC)"

logs-api: ## Afficher les logs de l'API
	@cd .. && docker-compose logs -f

full-test: verify-env start-api test stop-api ## Cycle complet: démarrer API, tester, arrêter
	@echo "$(GREEN)✓ Cycle de test complet terminé$(NC)"

ci-test: verify-env install ## Tests pour CI/CD (sans démarrage API)
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Tests CI/CD$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	$(PYTEST) -v --tb=short --cov=../api --cov-report=xml --cov-report=term

report: ## Afficher le résumé du dernier test
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Résumé des tests$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@if [ -f htmlcov/index.html ]; then \
		echo "$(GREEN)✓ Rapport de couverture disponible: htmlcov/index.html$(NC)"; \
	else \
		echo "$(YELLOW)! Aucun rapport de couverture. Lancer: make test-coverage$(NC)"; \
	fi
