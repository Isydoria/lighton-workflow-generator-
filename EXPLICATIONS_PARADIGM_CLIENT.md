# 📚 Explications ParadigmClient pour débutants

## 🎯 Ce qu'on va faire aujourd'hui

On va améliorer le "facteur" (ParadigmClient) qui va chercher des informations dans l'API Paradigm.

---

## 🔍 Partie 1 : Ce qui existe déjà

### Dans le fichier `api/api_clients.py`

Imagine ce fichier comme un **bureau de poste** 📬 avec plusieurs guichets :

#### Guichet 1 : `paradigm_document_search()`
**Ce qu'il fait** : Cherche des documents
```python
# Exemple d'utilisation
result = await paradigm_document_search("Quel est le montant total ?", file_ids=[123])
```

**Comment ça marche** :
1. Tu donnes une question : "Quel est le montant total ?"
2. Tu donnes des fichiers où chercher : `file_ids=[123]`
3. L'API Paradigm cherche dans les fichiers
4. Elle te répond : "Le montant total est 1500€"

#### Guichet 2 : `paradigm_analyze_documents_with_polling()`
**Ce qu'il fait** : Analyse des documents (peut prendre du temps)
```python
# Exemple d'utilisation
result = await paradigm_analyze_documents_with_polling(
    "Analyser ce document",
    document_ids=[123, 456]
)
```

**Comment ça marche** :
1. Tu demandes une analyse : "Analyser ce document"
2. L'API commence l'analyse (ça peut prendre 1-5 minutes)
3. La fonction **attend automatiquement** (polling) :
   - Toutes les 5 secondes, elle demande : "C'est fini ?"
   - Si non → Elle attend encore 5 secondes
   - Si oui → Elle te donne les résultats
4. Maximum 5 minutes d'attente (timeout = 300 secondes)

**Analogie** 🎓 :
C'est comme attendre un colis :
- Tu commandes (start analysis)
- Chaque jour tu vérifies ta boîte aux lettres (polling toutes les 5s)
- Quand le colis arrive, tu l'ouvres (return result)

---

## 🚀 Partie 2 : Ce qu'on va ajouter

### Amélioration 1 : VisionDocumentSearch (fallback)

**Problème actuel** :
Parfois, la recherche normale ne trouve rien :
- Document scanné de travers
- Mauvaise qualité d'OCR (reconnaissance de texte)
- Tableaux complexes

**Solution : Utiliser vision comme plan B**

```python
# AVANT (ce qu'on a actuellement)
result = await paradigm_document_search("Montant total ?", file_ids=[123])
# Si ça rate → On abandonne ❌

# APRÈS (ce qu'on va ajouter)
result = await paradigm_document_search("Montant total ?", file_ids=[123])
if not result or "not found" in result:
    # Plan B : Essayer avec vision
    result = await paradigm_document_search(
        "Montant total ?",
        file_ids=[123],
        tool="VisionDocumentSearch"  # ← Mode vision
    )
```

**Analogie** 🎓 :
- **Méthode normale** = Lire un livre avec tes yeux
- **Vision** = Regarder une photo du livre avec une loupe

---

### Amélioration 2 : Classe ParadigmClient standalone

**Problème** :
Actuellement, le code est dans `api/api_clients.py` :
- ✅ Parfait pour le Workflow Builder (notre app)
- ❌ Difficile à copier pour les clients

**Solution** :
Créer une **classe standalone** = un fichier qu'on peut copier-coller tel quel

```python
# Fichier : api/paradigm_client_standalone.py

class ParadigmClient:
    """
    Client Paradigm 100% autonome.
    Peut être copié tel quel dans n'importe quel projet.
    """

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    async def document_search(self, query: str, **kwargs):
        # Toute la logique incluse
        pass

    async def analyze_documents_with_polling(self, query: str, document_ids: list):
        # Polling inclus
        pass
```

**Avantages** :
- ✅ **Portable** : On copie ce fichier dans le package client
- ✅ **Indépendant** : Pas besoin du reste du code
- ✅ **Complet** : Tout est inclus (polling, fallback, etc.)

**Analogie** 🎓 :
- **Code actuel** = Recette de cuisine éparpillée dans plusieurs livres
- **Classe standalone** = Recette complète sur une seule fiche

---

## 📝 Partie 3 : Exemple concret

### Scénario : Extraire le montant d'une facture

#### Avec le code amélioré

```python
# 1. Créer le client
paradigm = ParadigmClient(
    api_key="ta_cle_api",
    base_url="https://api.lighton.ai"
)

# 2. Essayer recherche normale
result = await paradigm.document_search(
    "Quel est le montant total de cette facture ?",
    file_ids=[456]
)

# 3. Fallback automatique si nécessaire
if not result or "not found" in result.lower():
    print("⚠️ Recherche normale échouée, essai avec vision...")
    result = await paradigm.document_search(
        "Quel est le montant total de cette facture ?",
        file_ids=[456],
        tool="VisionDocumentSearch"  # Plan B
    )

# 4. Utiliser le résultat
print(f"Montant trouvé : {result}")
```

#### Avec polling (analyse longue)

```python
# Si l'analyse prend du temps (1-5 minutes)
analysis = await paradigm.analyze_documents_with_polling(
    query="Analyser cette facture en détail",
    document_ids=[456, 457, 458]
)

# La fonction attend automatiquement !
# Tu n'as rien à faire, elle gère le polling
print(f"Analyse complète : {analysis}")
```

---

## 🛠️ Partie 4 : Plan d'action

### Étape 1 ✅ : Analyser le code existant
**Fait !** On a vu que le polling existe déjà.

### Étape 2 🔄 : Ajouter VisionDocumentSearch
**En cours !** On va modifier `paradigm_document_search()`.

### Étape 3 : Créer la classe standalone
On va créer `api/paradigm_client_standalone.py`.

### Étape 4 : Documenter
On va ajouter des explications dans le code.

### Étape 5 : Tester
On va tester avec un vrai workflow.

---

## 🤔 Questions fréquentes

### Q1 : Pourquoi VisionDocumentSearch ?
**R** : Parfois le texte est mal reconnu (OCR). Vision regarde le document comme une image → plus robuste.

### Q2 : C'est quoi "polling" ?
**R** : Vérifier régulièrement si quelque chose est prêt. Comme vérifier ta boîte aux lettres chaque jour pour un colis.

### Q3 : Pourquoi créer une classe standalone ?
**R** : Pour que les clients puissent copier le fichier tel quel sans dépendance. Comme une recette complète sur une fiche.

### Q4 : Le polling actuel est-il bon ?
**R** : OUI ! Le code actuel est déjà excellent. On ajoute juste le fallback vision.

### Q5 : Combien de temps prend le polling ?
**R** :
- Vérification toutes les 5 secondes
- Maximum 5 minutes (300 secondes)
- Si l'analyse prend plus → timeout

---

## 📊 Comparaison : Avant vs Après

| Aspect | Avant | Après |
|--------|-------|-------|
| **Recherche** | Document search uniquement | + VisionDocumentSearch (fallback) |
| **Polling** | ✅ Déjà présent | ✅ Conservé |
| **Portabilité** | Code éparpillé | Classe standalone |
| **Robustesse** | 1 méthode | Multiple méthodes (fallback) |
| **Pour clients** | Difficile à copier | Facile à déployer |

---

## 🎓 Vocabulaire technique

- **API** : Interface qui permet de communiquer avec un service (comme un guichet)
- **Polling** : Vérifier régulièrement l'état d'une opération
- **Fallback** : Plan B si le plan A échoue
- **Standalone** : Autonome, qui fonctionne tout seul
- **OCR** : Reconnaissance de texte dans une image
- **Vision** : Analyse d'un document comme une image (pas comme du texte)
- **Timeout** : Temps maximum d'attente avant d'abandonner

---

**Version** : 1.0
**Date** : 21/11/2025
**Auteur** : Nathanaëlle (avec Claude Code)
