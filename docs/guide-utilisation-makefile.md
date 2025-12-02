# Guide d'Utilisation du Makefile - LightOn Workflow Builder

**Date:** 02 décembre 2025
**Version:** 1.0.0
**Pour:** Développeurs et utilisateurs du projet

---

## Table des Matières

1. [Introduction](#introduction)
2. [Prérequis](#prérequis)
3. [Installation Initiale](#installation-initiale)
4. [Démarrage Rapide](#démarrage-rapide)
5. [Commandes Développement Local](#commandes-développement-local)
6. [Commandes Docker](#commandes-docker)
7. [Tests et Qualité](#tests-et-qualité)
8. [Utilitaires](#utilitaires)
9. [Workflows Courants](#workflows-courants)
10. [Troubleshooting](#troubleshooting)
11. [Variables d'Environnement](#variables-denvironnement)

---

## Introduction

Le Makefile à la racine du projet fournit une interface unifiée pour gérer le cycle de vie de l'application LightOn Workflow Builder. Il remplace et améliore les scripts batch Windows (dev.bat) avec des fonctionnalités supplémentaires.

### Avantages

- ✅ **Simplicité** : Une seule commande pour démarrer l'application
- ✅ **Multi-plateforme** : Fonctionne sur Linux, macOS et Windows (avec Make)
- ✅ **Gestion automatique** : Installation des dépendances, vérification de configuration
- ✅ **Logs persistants** : Fichiers backend.log et frontend.log
- ✅ **Support Docker** : Commandes Docker intégrées
- ✅ **Tests intégrés** : Accès direct à la suite de tests
- ✅ **Code quality** : Formatage et linting

---

## Prérequis

### Obligatoires

- **Python 3.11+** : `python3 --version`
- **Make** : `make --version`
- **Git** : `git --version`

### Optionnels

- **Docker** : Pour utiliser les commandes `docker-*`
- **Docker Compose** : Pour orchestration des conteneurs

### Installation de Make

#### Linux
```bash
sudo apt-get install make  # Debian/Ubuntu
sudo yum install make      # CentOS/RHEL
```

#### macOS
```bash
brew install make
```

#### Windows
```bash
# Avec Chocolatey
choco install make

# Avec WSL (recommandé)
wsl --install
```

---

## Installation Initiale

### 1. Cloner le Projet

```bash
git clone git@gitlab.lighton.ai:paradigm/usescases/workflowbuilder.git
cd workflowbuilder
```

### 2. Configurer les Variables d'Environnement

Créer un fichier `.env` à partir du template :

```bash
cp .env.example .env
```

Éditer `.env` et renseigner les clés API :

```bash
# Clés API (OBLIGATOIRES)
ANTHROPIC_API_KEY=sk-ant-your-key-here
LIGHTON_API_KEY=your-lighton-key-here

# URLs (OPTIONNELLES)
PARADIGM_API_BASE_URL=https://paradigm.lighton.ai

# Redis (OPTIONNEL - pour Vercel/Upstash)
KV_REST_API_URL=
KV_REST_API_TOKEN=
```

### 3. Installer les Dépendances

```bash
make install
```

Cette commande va :
1. Créer un environnement virtuel Python (`.venv`)
2. Mettre à jour pip
3. Installer toutes les dépendances depuis `requirements.txt`

### 4. Vérifier la Configuration

```bash
make verify-env
```

Vous devriez voir :
```
✓ ANTHROPIC_API_KEY définie
✓ LIGHTON_API_KEY définie
✓ Configuration OK
```

---

## Démarrage Rapide

### Lancer l'Application Complète

```bash
make dev
```

Cela va :
1. Arrêter les anciens serveurs
2. Vérifier les variables d'environnement
3. Démarrer le backend sur le port 8000
4. Démarrer le frontend sur le port 3000

**Accès** :
- **Frontend** : http://localhost:3000
- **Backend API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs

### Arrêter l'Application

```bash
make stop
```

### Voir les Logs

```bash
# Logs en temps réel
make logs

# Ou directement
tail -f backend.log
tail -f frontend.log
```

---

## Commandes Développement Local

### Afficher l'Aide

```bash
make help
# ou simplement
make
```

### Installation et Configuration

| Commande | Description |
|----------|-------------|
| `make install` | Installer les dépendances Python |
| `make install-dev` | Installer + dépendances de développement (pytest, etc.) |
| `make verify-env` | Vérifier les variables d'environnement |

**Exemple** :
```bash
# Installation complète pour le développement
make install-dev
```

### Démarrage de l'Application

| Commande | Description |
|----------|-------------|
| `make dev` | Démarrer backend + frontend |
| `make dev-backend` | Démarrer uniquement le backend (port 8000) |
| `make dev-frontend` | Démarrer uniquement le frontend (port 3000) |
| `make stop` | Arrêter tous les serveurs |

**Exemple** :
```bash
# Démarrer uniquement le backend pour des tests API
make dev-backend

# Dans un autre terminal, démarrer le frontend
make dev-frontend
```

### Monitoring et Logs

| Commande | Description |
|----------|-------------|
| `make health` | Vérifier que l'API répond |
| `make logs` | Afficher les logs en temps réel |

**Exemple** :
```bash
# Vérifier que l'API est démarrée
make health

# Résultat attendu :
# {
#   "status": "healthy",
#   "version": "1.16.0"
# }
```

### Nettoyage

| Commande | Description |
|----------|-------------|
| `make clean` | Nettoyer fichiers temporaires (logs, cache) |
| `make clean-all` | Nettoyer tout y compris l'environnement virtuel |

**Exemple** :
```bash
# Avant de réinstaller les dépendances
make clean-all
make install
```

---

## Commandes Docker

### Démarrage avec Docker

| Commande | Description |
|----------|-------------|
| `make docker-build` | Construire l'image Docker |
| `make docker-up` | Démarrer l'application avec Docker Compose |
| `make docker-down` | Arrêter et supprimer les conteneurs |
| `make docker-restart` | Redémarrer les conteneurs |

**Workflow Docker** :
```bash
# Première fois
make docker-build
make docker-up

# Arrêter
make docker-down

# Redémarrer après modifications
make docker-build
make docker-up
```

### Gestion Docker

| Commande | Description |
|----------|-------------|
| `make docker-logs` | Afficher les logs des conteneurs |
| `make docker-ps` | Lister les conteneurs en cours d'exécution |
| `make docker-shell` | Ouvrir un shell dans le conteneur |
| `make docker-clean` | Nettoyer conteneurs et images |

**Exemple** :
```bash
# Déboguer dans le conteneur
make docker-shell

# Dans le conteneur :
root@container:/app# ls
root@container:/app# python --version
root@container:/app# exit
```

---

## Tests et Qualité

### Lancer les Tests

```bash
# Tous les tests
make test

# Tests spécifiques (dans le dossier tests/)
cd tests
make test-paradigm      # Tests Paradigm API
make test-workflow      # Tests Workflows
make test-integration   # Tests d'intégration
make test-security      # Tests de sécurité
```

**Sortie attendue** :
```
═══════════════════════════════════════════════════════════
  Lancement de tous les tests
═══════════════════════════════════════════════════════════
pytest -v --tb=short --cov=../api --cov-report=term-missing

======================== test session starts ========================
tests/test_paradigm_api.py::test_document_search_basic PASSED [ 10%]
tests/test_workflow_api.py::test_create_workflow PASSED    [ 20%]
...
======================== 97 passed in 45.3s =========================
```

### Code Quality

| Commande | Description |
|----------|-------------|
| `make format` | Formater le code avec black |
| `make lint` | Linter le code avec flake8 |

**Exemple** :
```bash
# Avant de commiter
make format
make lint
```

---

## Utilitaires

### Vérifier la Santé de l'API

```bash
make health
```

**Résultat** :
```json
{
  "status": "healthy",
  "version": "1.16.0",
  "redis": "connected"
}
```

### Accéder à la Documentation API

Une fois l'application démarrée :
```bash
make dev
# Ouvrir http://localhost:8000/docs
```

La documentation interactive Swagger UI permet de tester tous les endpoints.

---

## Workflows Courants

### Workflow 1 : Développement Quotidien

```bash
# Matin : démarrer l'application
make dev

# Vérifier que tout fonctionne
make health

# Développer...
# Les modifications sont auto-rechargées (--reload)

# Soir : arrêter
make stop
```

### Workflow 2 : Nouvelle Feature

```bash
# 1. Créer une branche
git checkout -b feature/ma-nouvelle-feature

# 2. Installer les dépendances de dev
make install-dev

# 3. Développer avec auto-reload
make dev-backend

# 4. Tester
make test

# 5. Formatter et linter
make format
make lint

# 6. Commiter
git add .
git commit -m "feat: Ma nouvelle feature"

# 7. Pousser
git push origin feature/ma-nouvelle-feature
```

### Workflow 3 : Debug d'un Problème

```bash
# 1. Arrêter tous les serveurs
make stop

# 2. Nettoyer
make clean

# 3. Réinstaller les dépendances
make install

# 4. Démarrer en mode debug
make dev-backend

# 5. Dans un autre terminal, voir les logs
make logs

# 6. Tester l'API
curl http://localhost:8000/health
```

### Workflow 4 : Test avant Production

```bash
# 1. Construire l'image Docker
make docker-build

# 2. Démarrer avec Docker
make docker-up

# 3. Tester
make test

# 4. Vérifier les logs
make docker-logs

# 5. Si OK, déployer
make docker-down
```

### Workflow 5 : Contribution au Projet

```bash
# 1. Fork et clone
git clone git@gitlab.lighton.ai:your-username/workflowbuilder.git
cd workflowbuilder

# 2. Installer
make install-dev

# 3. Créer une branche
git checkout -b fix/mon-bug-fix

# 4. Développer
make dev

# 5. Tester toute la suite
make test

# 6. Vérifier la qualité du code
make format
make lint

# 7. Commiter selon les conventions
git commit -m "fix: Correction du bug XYZ"

# 8. Pousser et créer une Merge Request
git push origin fix/mon-bug-fix
```

---

## Troubleshooting

### Problème : "make: command not found"

**Solution** :
```bash
# Linux
sudo apt-get install make

# macOS
brew install make

# Windows
# Installer via WSL ou Chocolatey
```

### Problème : "ANTHROPIC_API_KEY non définie"

**Solution** :
```bash
# 1. Vérifier que le fichier .env existe
ls -la .env

# 2. Si non, créer depuis .env.example
cp .env.example .env

# 3. Éditer .env et ajouter les clés
nano .env  # ou vim, code, etc.

# 4. Vérifier
make verify-env
```

### Problème : "Port 8000 already in use"

**Solution** :
```bash
# Arrêter tous les serveurs Python
make stop

# Si persiste, tuer manuellement
lsof -ti:8000 | xargs kill -9

# Ou sur un autre port
BACKEND_PORT=8001 make dev-backend
```

### Problème : "ModuleNotFoundError"

**Solution** :
```bash
# Réinstaller les dépendances
make clean-all
make install

# Ou forcer la réinstallation
rm -rf .venv
make install
```

### Problème : "Docker: Cannot connect to the Docker daemon"

**Solution** :
```bash
# Démarrer Docker
sudo systemctl start docker  # Linux
open -a Docker              # macOS

# Ou utiliser le mode développement local
make dev
```

### Problème : Tests échouent

**Solution** :
```bash
# 1. Vérifier que l'API est démarrée
make dev
make health

# 2. Vérifier les variables d'environnement
cd tests
cat .env

# 3. Lancer les tests avec plus de détails
cd tests
make test-verbose
```

### Problème : Logs introuvables

**Solution** :
```bash
# Vérifier que l'application est démarrée
ps aux | grep uvicorn

# Les logs sont créés à la première exécution de make dev
make dev
# Attendre 3 secondes
make logs
```

### Problème : Permission denied sur les scripts

**Solution** :
```bash
# Donner les permissions d'exécution
chmod +x Makefile

# Sur les fichiers .sh si présents
find . -name "*.sh" -exec chmod +x {} \;
```

---

## Variables d'Environnement

### Variables Obligatoires

| Variable | Description | Exemple |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Clé API Anthropic Claude | `sk-ant-api03-...` |
| `LIGHTON_API_KEY` | Clé API LightOn Paradigm | `your-lighton-key` |

### Variables Optionnelles

| Variable | Description | Défaut | Exemple |
|----------|-------------|--------|---------|
| `PARADIGM_API_BASE_URL` | URL base Paradigm API | `https://paradigm.lighton.ai` | Custom URL |
| `KV_REST_API_URL` | URL Vercel KV Redis | - | `https://...vercel-storage.com` |
| `KV_REST_API_TOKEN` | Token Vercel KV | - | `AXd...` |
| `UPSTASH_REDIS_REST_URL` | URL Upstash Redis | - | `https://...upstash.io` |
| `UPSTASH_REDIS_REST_TOKEN` | Token Upstash | - | `AYb...` |

### Variables de Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `BACKEND_PORT` | Port du backend | `8000` |
| `FRONTEND_PORT` | Port du frontend | `3000` |
| `PYTHON` | Commande Python | `python3` |
| `VENV` | Chemin environnement virtuel | `.venv` |

**Override des variables** :
```bash
# Changer le port du backend
BACKEND_PORT=9000 make dev-backend

# Utiliser python au lieu de python3
PYTHON=python make install
```

### Fichier .env.example

Le fichier [.env.example](.env.example) contient un template :

```bash
# Clés API (OBLIGATOIRES)
ANTHROPIC_API_KEY=your_anthropic_key_here
LIGHTON_API_KEY=your_lighton_key_here

# Configuration API (OPTIONNEL)
PARADIGM_API_BASE_URL=https://paradigm.lighton.ai

# Redis pour Vercel KV (OPTIONNEL)
KV_REST_API_URL=
KV_REST_API_TOKEN=

# Redis pour Upstash (OPTIONNEL)
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```

---

## Commandes Avancées

### Personnaliser les Ports

```bash
# Backend sur 9000, Frontend sur 4000
BACKEND_PORT=9000 FRONTEND_PORT=4000 make dev
```

### Utiliser un Python Spécifique

```bash
# Utiliser Python 3.12
PYTHON=python3.12 make install
```

### Mode Debug Avancé

```bash
# Démarrer le backend avec plus de logs
. .venv/bin/activate
LOG_LEVEL=DEBUG uvicorn api.main:app --reload --port 8000
```

### Exécuter des Commandes dans le Virtualenv

```bash
# Activer le venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Utiliser les outils
python api/main.py
pytest tests/

# Désactiver
deactivate
```

---

## Intégration CI/CD

### GitLab CI

Exemple de `.gitlab-ci.yml` :

```yaml
stages:
  - install
  - test
  - build
  - deploy

variables:
  ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
  LIGHTON_API_KEY: $LIGHTON_API_KEY

install:
  stage: install
  script:
    - make install
  cache:
    paths:
      - .venv/

test:
  stage: test
  script:
    - make test
  dependencies:
    - install

build:
  stage: build
  script:
    - make docker-build
  only:
    - main

deploy:
  stage: deploy
  script:
    - make docker-up
  only:
    - main
  when: manual
```

### GitHub Actions

Exemple de `.github/workflows/test.yml` :

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: make install

      - name: Run tests
        run: make test
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LIGHTON_API_KEY: ${{ secrets.LIGHTON_API_KEY }}
```

---

## Référence Complète des Commandes

### Développement Local

```bash
make help              # Afficher l'aide
make install           # Installer les dépendances
make install-dev       # Installer + dev dependencies
make verify-env        # Vérifier variables d'environnement
make dev               # Démarrer backend + frontend
make dev-backend       # Démarrer uniquement backend
make dev-frontend      # Démarrer uniquement frontend
make stop              # Arrêter tous les serveurs
make health            # Vérifier santé de l'API
make logs              # Afficher logs en temps réel
make test              # Lancer les tests
make clean             # Nettoyer fichiers temporaires
make clean-all         # Nettoyer tout + venv
make format            # Formater le code
make lint              # Linter le code
```

### Docker

```bash
make docker-build      # Construire l'image
make docker-up         # Démarrer avec Docker Compose
make docker-down       # Arrêter les conteneurs
make docker-restart    # Redémarrer les conteneurs
make docker-logs       # Afficher les logs
make docker-ps         # Lister les conteneurs
make docker-shell      # Shell dans le conteneur
make docker-clean      # Nettoyer Docker
```

---

## Bonnes Pratiques

### 1. Toujours Vérifier l'Environnement

```bash
make verify-env
```

Avant de démarrer le développement.

### 2. Nettoyer Régulièrement

```bash
make clean
```

Une fois par semaine ou avant un git pull.

### 3. Utiliser les Logs

```bash
make logs
```

Plutôt que d'afficher dans la console.

### 4. Tester Avant de Commiter

```bash
make test
make format
make lint
```

Pour éviter les erreurs en CI/CD.

### 5. Utiliser Docker pour Production

```bash
make docker-build
make docker-up
```

Pour un environnement reproductible.

---

## Support et Ressources

### Documentation

- [README principal](../README.md)
- [Analyse de conformité](./analyse-conformite-architecture.md)
- [Tests README](../tests/README.md)

### Liens Utiles

- **Repository** : `git@gitlab.lighton.ai:paradigm/usescases/workflowbuilder.git`
- **Documentation Paradigm API** : https://paradigm.lighton.ai/docs
- **Documentation Anthropic** : https://docs.anthropic.com

### Obtenir de l'Aide

```bash
# Afficher l'aide du Makefile
make help

# Afficher l'aide des tests
cd tests && make help
```

### Signaler un Bug

Si une commande ne fonctionne pas :
1. Vérifier les prérequis
2. Consulter le Troubleshooting
3. Créer une issue sur GitLab avec :
   - La commande exécutée
   - Le message d'erreur complet
   - Votre système d'exploitation
   - La version de Python et Make

---

## Changelog du Makefile

### Version 1.0.0 (2025-12-02)

**Ajout** :
- Commandes de développement local
- Support Docker complet
- Tests intégrés
- Code quality (format, lint)
- Health checks
- Logs persistants
- Vérification automatique des variables d'environnement

**Améliorations par rapport à dev.bat** :
- Multi-plateforme (Linux, macOS, Windows)
- Gestion automatique des dépendances
- Logs dans des fichiers
- Support des tests
- Commandes Docker
- Code formatting et linting

---

**Document maintenu par** : Architecture Team
**Dernière mise à jour** : 02/12/2025
**Version du Makefile** : 1.0.0
