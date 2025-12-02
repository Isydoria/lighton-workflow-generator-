# Tests - LightOn Workflow Builder

Suite de tests complète pour les endpoints Paradigm API et l'API backend.

## 📋 Vue d'ensemble

Cette suite de tests couvre :
- ✅ **11 endpoints Paradigm API** (document-search, document-analysis, files, chunks, etc.)
- ✅ **Endpoints backend** (workflows, exécution, files, PDF export)
- ✅ **Tests d'intégration** end-to-end
- ✅ **Tests de sécurité** du sandbox
- ✅ **Tests de performance** et concurrence

## 🚀 Démarrage Rapide

```bash
# Installer les dépendances
make install

# Vérifier les variables d'environnement
make verify-env

# Lancer tous les tests
make test

# Tests rapides uniquement
make test-quick
```

## 📦 Structure

```
tests/
├── Makefile                    # Commandes de test
├── conftest.py                 # Configuration pytest
├── test_paradigm_api.py        # Tests endpoints Paradigm (11 endpoints)
├── test_workflow_api.py        # Tests workflows (création, exécution)
├── test_files_api.py           # Tests fichiers (upload, query)
├── test_integration.py         # Tests end-to-end
├── test_security.py            # Tests sécurité sandbox
└── README.md                   # Ce fichier
```

## 🔧 Configuration

### Variables d'Environnement Requises

Créer un fichier `.env` à la racine du projet :

```bash
# Clés API
LIGHTON_API_KEY=your_lighton_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# URLs (optionnel)
API_BASE_URL=http://localhost:8000
PARADIGM_BASE_URL=https://paradigm.lighton.ai
```

### Installation

```bash
# Installer pytest et dépendances
make install

# Vérifier la configuration
make verify-env

# Vérifier que l'API backend répond
make check-api
```

## 🧪 Commandes de Test

### Tests Généraux

```bash
make test              # Tous les tests avec couverture
make test-quick        # Tests rapides uniquement (sans slow)
make test-smoke        # Test rapide de santé de l'API
make test-verbose      # Tests en mode très verbeux
make test-failed       # Relancer uniquement les tests échoués
```

### Tests par Catégorie

```bash
make test-paradigm     # Tests endpoints Paradigm API
make test-workflow     # Tests création/exécution workflows
make test-files        # Tests upload/gestion fichiers
make test-integration  # Tests scénarios end-to-end
make test-security     # Tests sécurité sandbox
```

### Couverture et Rapports

```bash
make test-coverage     # Générer rapport de couverture HTML
make report            # Afficher résumé du dernier test
```

### Gestion de l'API

```bash
make start-api         # Démarrer l'API backend
make stop-api          # Arrêter l'API backend
make check-api         # Vérifier que l'API répond
make logs-api          # Afficher les logs de l'API
```

### Workflow Complet

```bash
make full-test         # Cycle complet: démarrer API → tester → arrêter
make ci-test           # Tests pour CI/CD (sans démarrage API)
```

### Utilitaires

```bash
make clean             # Nettoyer fichiers de test
make help              # Afficher l'aide
```

## 📊 Tests Paradigm API

### Endpoints Testés (11/11)

| Endpoint | Tests | Status |
|----------|-------|--------|
| `POST /api/v2/chat/document-search` | 3 tests | ✅ |
| `POST /api/v2/chat/document-analysis` | 2 tests | ✅ |
| `POST /api/v2/chat/completions` | 2 tests | ✅ |
| `POST /api/v2/files` | 5 tests | ✅ |
| `GET /api/v2/files/{id}` | 3 tests | ✅ |
| `POST /api/v2/files/{id}/ask` | 4 tests | ✅ |
| `GET /api/v2/files/{id}/chunks` | 1 test | ✅ |
| `POST /api/v2/filter/chunks` | 1 test | ✅ |
| `POST /api/v2/query` | 1 test | ✅ |
| `POST /api/v2/chat/image-analysis` | 1 test | ✅ |
| Gestion d'erreurs | 3 tests | ✅ |

**Total: 26 tests pour Paradigm API**

### Exemples de Tests Paradigm

```bash
# Test recherche sémantique
pytest tests/test_paradigm_api.py::TestParadigmDocumentSearch::test_document_search_basic -v

# Test upload de fichier
pytest tests/test_paradigm_api.py::TestParadigmFiles::test_file_upload -v

# Test chat completion
pytest tests/test_paradigm_api.py::TestParadigmChatCompletions::test_chat_completion_basic -v
```

## 📊 Tests Backend API

### Endpoints Testés

| Catégorie | Endpoints | Tests |
|-----------|-----------|-------|
| Workflows | 7 endpoints | 15 tests |
| Files | 4 endpoints | 18 tests |
| Exécution | 3 endpoints | 8 tests |
| Export PDF | 1 endpoint | 2 tests |

**Total: 43 tests backend**

### Exemples de Tests Backend

```bash
# Test création workflow
pytest tests/test_workflow_api.py::TestWorkflowCreation::test_create_simple_workflow -v

# Test exécution workflow
pytest tests/test_workflow_api.py::TestWorkflowExecution::test_execute_simple_workflow -v

# Test upload fichier
pytest tests/test_files_api.py::TestFileUpload::test_upload_text_file -v
```

## 🔗 Tests d'Intégration

Tests de scénarios utilisateur complets :

```bash
# Cycle complet: Upload → Workflow → Exécution → PDF
pytest tests/test_integration.py::TestCompleteUserJourney -v

# Workflow avec recherche de documents
pytest tests/test_integration.py::TestFileToWorkflowIntegration -v

# Exécution parallèle de workflows
pytest tests/test_integration.py::TestMultipleWorkflowsParallel -v
```

**Total: 12 tests d'intégration**

## 🔒 Tests de Sécurité

Tests des vulnérabilités identifiées dans l'analyse :

```bash
# Tests sandbox (accès fichiers, OS, imports)
pytest tests/test_security.py::TestSandboxSecurity -v

# Tests validation d'entrées (XSS, SQL injection)
pytest tests/test_security.py::TestInputValidation -v

# Tests exposition clés API
pytest tests/test_security.py::TestAPIKeyExposure -v
```

**Total: 16 tests de sécurité**

### Vulnérabilités Testées

- ⚠️ Accès système de fichiers
- ⚠️ Injection de commandes OS
- ⚠️ Import de modules dangereux
- ⚠️ Utilisation de eval/exec
- ⚠️ Épuisement mémoire
- ⚠️ Boucles infinies
- ⚠️ Exposition de clés API
- ⚠️ Rate limiting
- ⚠️ CORS permissif

## 🎯 Markers Pytest

Utiliser les markers pour filtrer les tests :

```bash
# Tests par catégorie
pytest -m paradigm      # Tests Paradigm API
pytest -m workflow      # Tests Workflow API
pytest -m files         # Tests Files API
pytest -m integration   # Tests d'intégration
pytest -m security      # Tests de sécurité

# Exclure tests lents
pytest -m "not slow"

# Combiner markers
pytest -m "paradigm and not slow"
```

## 📈 Couverture de Code

```bash
# Générer rapport de couverture
make test-coverage

# Ouvrir le rapport HTML
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Objectif : **> 80% de couverture**

## ⚡ Performance

### Tests de Performance

```bash
# Requêtes concurrentes
pytest tests/test_paradigm_api.py::TestParadigmPerformance -v

# Workflows parallèles
pytest tests/test_workflow_api.py::TestWorkflowConcurrency -v
```

### Benchmark

```bash
# Lancer les benchmarks
make benchmark
```

## 🐛 Debugging

### Tests Verbeux

```bash
# Afficher toutes les sorties
pytest -vv --tb=long

# Afficher print statements
pytest -s

# Arrêter au premier échec
pytest -x
```

### Tests Spécifiques

```bash
# Lancer un test spécifique
pytest tests/test_paradigm_api.py::TestParadigmDocumentSearch::test_document_search_basic -v

# Lancer une classe de tests
pytest tests/test_workflow_api.py::TestWorkflowCreation -v

# Lancer un fichier
pytest tests/test_files_api.py -v
```

### Mode Watch

```bash
# Relancer automatiquement lors de changements
make test-watch
```

## 🔄 CI/CD

### GitHub Actions / GitLab CI

```yaml
# Exemple configuration CI
test:
  script:
    - cd tests
    - make install
    - make verify-env
    - make ci-test
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Variables CI/CD Requises

```
LIGHTON_API_KEY
ANTHROPIC_API_KEY
```

## 📝 Écrire de Nouveaux Tests

### Template de Test

```python
import pytest
import httpx

@pytest.mark.asyncio
@pytest.mark.paradigm  # ou workflow, files, etc.
async def test_my_feature(api_headers):
    """Description du test"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Arrange
        payload = {"key": "value"}

        # Act
        response = await client.post(
            f"{API_BASE_URL}/endpoint",
            headers=api_headers,
            json=payload
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

### Bonnes Pratiques

1. **Utiliser les fixtures** pour le setup/cleanup
2. **Markers appropriés** (paradigm, workflow, files, security, slow)
3. **Tests atomiques** : un test = une fonctionnalité
4. **Noms descriptifs** : `test_what_when_expected`
5. **Assertions claires** avec messages d'erreur
6. **Cleanup** : supprimer les ressources créées
7. **Timeouts** : toujours définir un timeout

## 📊 Statistiques

### Résumé

- **Total de tests** : ~97 tests
- **Couverture** : 11/11 endpoints Paradigm API
- **Temps d'exécution** : ~5-10 minutes (tous les tests)
- **Tests rapides** : ~2 minutes

### Distribution

```
test_paradigm_api.py    : 26 tests (Paradigm API)
test_workflow_api.py    : 15 tests (Workflows)
test_files_api.py       : 18 tests (Files)
test_integration.py     : 12 tests (End-to-end)
test_security.py        : 16 tests (Sécurité)
---
Total                   : 97 tests
```

## 🔍 Troubleshooting

### Erreur: LIGHTON_API_KEY non définie

```bash
# Définir dans .env ou exporter
export LIGHTON_API_KEY=your_key_here
```

### Erreur: API ne répond pas

```bash
# Démarrer l'API backend
make start-api

# Vérifier les logs
make logs-api
```

### Tests qui timeout

```bash
# Augmenter les timeouts dans les tests
# Ou utiliser tests rapides
make test-quick
```

### Échecs de tests de sécurité

Les tests de sécurité **documentent les vulnérabilités** identifiées dans l'analyse. Certains échecs sont attendus et indiquent des améliorations nécessaires.

## 📚 Références

- [Pytest Documentation](https://docs.pytest.org/)
- [HTTPX Documentation](https://www.python-httpx.org/)
- [Paradigm API Documentation](https://paradigm.lighton.ai/docs)
- [Analyse de Conformité](../docs/analyse-conformite-architecture.md)

## 🤝 Contribution

Pour ajouter de nouveaux tests :

1. Suivre le template ci-dessus
2. Ajouter les markers appropriés
3. Mettre à jour ce README
4. Lancer `make test` avant de commiter

## 📞 Support

Pour toute question sur les tests, consulter :
- [Documentation principale](../README.md)
- [Analyse de conformité](../docs/analyse-conformite-architecture.md)
- Issues GitHub du projet
