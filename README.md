# Assistant Scolarité RAG — École d'Ingénieurs Hélianthe (EIH)

Système de Question-Réponse RAG (*Retrieval-Augmented Generation*) universitaire développé pour les étudiants de l'École d'Ingénieurs Hélianthe (EIH) à partir de ses règlements et documents officiels.

Projet réalisé dans le cadre du **Module RAG — Université Mundiapolis (3ACINFO)**.

---

## 1. Architecture générale
- **Corpus documentaire** : 7 documents administratifs PDF sous `data/corpus/`
- **Extraction & Découpage** : `pdfplumber`, découpage fixe ou structurel (articles, Q&A, sections)
- **Embeddings** : `intfloat/multilingual-e5-small` avec préfixes `passage:` et `query:`
- **Base Vectorielle** : `ChromaDB` persistée sur disque (`chroma_db/`)
- **Modèle de Génération** : LLM local Ollama (`llama3.1:8b`)
- **Backend API** : FastAPI + Pydantic v2 servi via `uvicorn`
- **Frontend** : Application Angular en TypeScript (`frontend/`)

---

## 2. Installation & Prérequis

### Prérequis
- Windows 10/11 avec PowerShell
- [uv](https://github.com/astral-sh/uv) (gestionnaire d'environnement et de paquets Python ultra-rapide)
- Python 3.11+
- [Ollama](https://ollama.com/) avec le modèle `llama3.1:8b` installé (`ollama run llama3.1:8b`)

### Configuration de l'environnement
1. Cloner le projet et créer le fichier d'environnement :
   ```powershell
   Copy-Item .env.example .env
   ```
2. Installer les dépendances :
   ```powershell
   uv sync
   ```
3. Enregistrer le kernel Jupyter pour VS Code :
   ```powershell
   .venv\Scripts\python -m ipykernel install --user --name assistant-scolarite --display-name "Python (assistant-scolarite)"
   ```

---

## 3. Utilisation

### Notebook principal
Ouvrir `notebooks/rag_eih.ipynb` dans VS Code, sélectionner le kernel **Python (assistant-scolarite)** et exécuter les cellules.
Le notebook est découpé en 5 séances (S1 à S5) auto-portées.
