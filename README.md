# LightOn Workflow Builder

Application de génération et d'exécution de workflows automatisés utilisant l'API Anthropic Claude et l'API LightOn Paradigm.

## 🚀 Démarrage Rapide

### Développement quotidien
Double-cliquez sur **`dev.bat`**
- Démarre le serveur en mode développement
- Frontend : http://localhost:3000
- Backend API : http://localhost:8000/docs

### Test avant déploiement
Double-cliquez sur **`test-docker.bat`**
- Teste l'application dans Docker (environnement de production)
- Vérifiez que tout fonctionne avant de déployer

## 📋 Prérequis

1. **Python 3.11+** installé
2. **Docker Desktop** (pour les tests Docker uniquement)
3. **Fichier .env** avec vos clés API :
   ```env
   ANTHROPIC_API_KEY=votre_clé_anthropic
   LIGHTON_API_KEY=votre_clé_lighton
   ```

## 🛠️ Workflow de Développement

```
1. Développer        → dev.bat
2. Tester            → http://localhost:3000
3. Test Docker       → test-docker.bat (avant commit)
4. Commit & Push     → git commit && git push
5. Déploiement       → Automatique sur Vercel
```

## ✨ Fonctionnalités

- **Natural Language to Code**: Décrivez vos workflows en langage naturel
- **LightOn Paradigm Integration**: Recherche et analyse de documents
- **Safe Code Execution**: Environnement d'exécution sécurisé avec timeout
- **RESTful API**: API FastAPI propre et bien documentée
- **Async Support**: Opérations asynchrones pour de meilleures performances

## 🔧 Installation Manuelle (si besoin)

1. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurer les clés API**

   Créez un fichier `.env` à la racine :
   ```bash
   ANTHROPIC_API_KEY=votre_clé_anthropic
   LIGHTON_API_KEY=votre_clé_lighton

   # Redis (optionnel - pour persistance serverless)
   # Vercel KV (automatique si lié depuis Vercel)
   KV_REST_API_URL=https://your-redis.upstash.io
   KV_REST_API_TOKEN=your_token_here

   # OU Upstash direct (configuration manuelle)
   UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
   UPSTASH_REDIS_REST_TOKEN=your_token_here
   ```

3. **Démarrer le serveur**
   ```bash
   # Utilisez plutôt dev.bat (recommandé)
   # Ou manuellement :
   python -m uvicorn api.index:app --port 8000
   ```

## API Usage

### 1. Create a Workflow

```bash
curl -X POST "http://localhost:8000/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "For each sentence in user input, search using paradigm_search, then format as Question: [sentence] Answer: [result]",
    "name": "Sentence Processing Workflow"
  }'
```

### 2. Execute a Workflow

```bash
curl -X POST "http://localhost:8000/workflows/{workflow_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "What is machine learning? How does AI work?"
  }'
```

### 3. Get Workflow Details

```bash
curl -X GET "http://localhost:8000/workflows/{workflow_id}"
```

## Example Workflow

The system is designed to handle workflows like the example provided:

**Description**: "User inputs a long prompt with multiple sentences. For each sentence, perform a search using the Paradigm Docsearch tool. Return results formatted as 'Question: [sentence]' followed by 'Answer: [result]'."

**Sample Input**: "What is machine learning? How does artificial intelligence work? What are the benefits of cloud computing?"

**Expected Output**:
```
Question: What is machine learning?
Answer: [Search result about machine learning]

Question: How does artificial intelligence work?
Answer: [Search result about AI]

Question: What are the benefits of cloud computing?
Answer: [Search result about cloud computing benefits]
```

## Available Tools in Workflows

Generated workflows have access to these tools:

- `paradigm_search(query: str) -> str`: Search documents using LightOn Paradigm
- `chat_completion(prompt: str) -> str`: Get AI responses using Anthropic API

## Testing

Run the example test to verify everything works:

```bash
python test_example.py
```

## 📁 Structure du Projet

```
├── api/                    # Backend FastAPI
│   ├── config.py          # Configuration (charge .env)
│   ├── main.py            # Application FastAPI
│   ├── models.py          # Modèles de données
│   ├── api_clients.py     # Clients API (Paradigm)
│   └── workflow/          # Générateur et exécuteur de workflows
├── index.html             # Frontend
├── .env                   # Variables d'environnement (NE PAS commiter!)
├── docker-compose.yml     # Configuration Docker
├── Dockerfile             # Image Docker
├── dev.bat               # Script de développement
└── test-docker.bat       # Script de test Docker
```

## 🐳 Déploiement

### Docker (test local)
```bash
# Build et démarrage
docker-compose up --build

# Arrêt
docker-compose down
```

### Vercel (production)
1. Connectez votre repo GitHub/GitLab à Vercel
2. Ajoutez les variables d'environnement dans Vercel :
   - `ANTHROPIC_API_KEY`
   - `LIGHTON_API_KEY`
3. Liez Vercel KV (Storage) :
   - Les variables `KV_REST_API_URL` et `KV_REST_API_TOKEN` sont créées automatiquement
   - Le code détecte et utilise ces variables automatiquement
4. Déployez : `git push` (automatique)

**Note** : Le code supporte automatiquement les deux conventions :
- Variables Vercel KV (créées automatiquement lors du linking)
- Variables Upstash directes (configuration manuelle)

## 📚 Documentation

- **API Backend** : http://localhost:8000/docs (quand le serveur tourne)
- **Docker** : Voir [DOCKER_README.md](DOCKER_README.md)
- **API Paradigm** : https://paradigm.lighton.ai/docs

## 🔒 Sécurité

- **Sandboxed Execution**: Le code s'exécute dans un environnement restreint
- **Timeout Protection**: Les exécutions sont limitées dans le temps
- **Input Validation**: Toutes les entrées sont validées
- **Error Handling**: Gestion complète des erreurs et logging

## 🐛 Dépannage

**Problème : "Port already in use"**
- Les scripts `dev.bat` et `test-docker.bat` tuent automatiquement les anciens serveurs
- Si problème persiste : `powershell "Get-Process python | Stop-Process -Force"`

**Problème : "API key not configured"**
- Vérifiez que le fichier `.env` existe à la racine du projet
- Vérifiez que les clés API sont correctes
- Redémarrez avec `dev.bat`

## 📝 Technologies

- **Backend** : FastAPI, Python 3.11+
- **Frontend** : HTML/CSS/JavaScript vanilla
- **AI** : Anthropic Claude API
- **Document Processing** : LightOn Paradigm API
- **Déploiement** : Vercel (prod), Docker (test)