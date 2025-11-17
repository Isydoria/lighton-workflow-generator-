# Feature: Smart Document Batching

## Objectif
Permettre au générateur de workflows de créer du code qui analyse les documents **séparément** ou **ensemble** selon la demande de l'utilisateur.

## Problème actuel
Le générateur crée toujours le même pattern : traitement par lots de 5 documents maximum. Cela ne convient pas à tous les cas d'usage.

## Solution proposée

### Détection automatique de l'intention
Analyser la description du workflow pour détecter :

**Analyse séparée** (1 appel API par document) :
- Mots-clés : "chaque", "séparément", "individuellement", "pour chaque document"
- Exemple : "Extraire le titre et le résumé de **chaque** document uploadé"
- Comportement : Boucle sur les documents, 1 appel `analyze_documents_with_polling([doc_id])` par document

**Analyse groupée** (1 appel API pour tous) :
- Mots-clés : "ensemble", "comparer", "croiser", "différences entre", "similitudes"
- Exemple : "**Comparer** les 2 documents uploadés et identifier les différences"
- Comportement : 1 seul appel `analyze_documents_with_polling([doc1, doc2, ...])`

**Par défaut** : Analyse groupée par lots de 5 (comportement actuel)

## Modifications nécessaires

### 1. Prompt du générateur (`api/workflow/generator.py`)
Ajouter une section expliquant :
- Comment détecter l'intention (séparé vs groupé)
- Exemples de code pour chaque cas
- Instructions claires sur quand utiliser chaque pattern

### 2. Exemples de code généré

#### Analyse séparée
```python
# Analyser chaque document individuellement
results = []
for doc_id in document_ids:
    analysis = await paradigm_client.analyze_documents_with_polling(
        query=f"Extraire le titre et résumé du document",
        document_ids=[str(doc_id)]
    )
    results.append({
        "document_id": doc_id,
        "analysis": analysis
    })
```

#### Analyse groupée
```python
# Analyser tous les documents ensemble
analysis = await paradigm_client.analyze_documents_with_polling(
    query="Comparer les documents et identifier les différences",
    document_ids=[str(id) for id in document_ids]
)
```

## Tests à effectuer

1. **Test séparé** : "Extraire le titre et résumé de chaque document uploadé"
   - Vérifier : 1 appel API par document
   - Vérifier : Résultats séparés clairement identifiés

2. **Test groupé** : "Comparer les 2 documents uploadés"
   - Vérifier : 1 seul appel API
   - Vérifier : Analyse comparative cohérente

3. **Test par défaut** : "Analyser les documents"
   - Vérifier : Comportement par lots de 5 (actuel)

## Priorité
**Medium** - Amélioration UX importante mais non bloquante

## Assigné à
À définir

## Date de création
17/01/2025
