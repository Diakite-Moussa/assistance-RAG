# Journal d'utilisation des outils d'IA générative (AI_LOG.md)

Projet : **Assistant Scolarité (RAG - École d'Ingénieurs Hélianthe EIH)**  
Cadre : Module RAG - Université Mundiapolis (3ACINFO)  
Date de début : 29 octobre 2026  

---

## Séance 0 : Initialisation de l'environnement et structure de base
- **Date** : 29/10/2026
- **Outil d'IA** : Antigravity (Modèle Gemini 3.8 Flash High)
- **Objectifs de l'étape** :
  - Mise en place du gestionnaire de dépendances `uv` avec Python 3.11+.
  - Nettoyage des artefacts et structuration de l'arborescence du projet (`notebooks/`, `eval/`, `frontend/`, `data/`, `chroma_db/`).
  - Configuration de `.gitignore` et `.env.example` / `.env`.
  - Installation des dépendances principales (`pdfplumber`, `chromadb`, `sentence-transformers`, `fastapi`, `uvicorn`, `httpx`, `pydantic`, `pydantic-settings`, etc.) et outils de dev (`ipykernel`, `ipytest`, `pytest`, `ruff`).
  - Enregistrement du noyau Jupyter `ipykernel` pour exécution dans VS Code.
  - Création du notebook principal `notebooks/rag_eih.ipynb` avec les sections S1 à S5 structurées.
  - Initialisation Git et premier commit propre.
- **Vérifications effectuées** :
  - Dépendances résolues et installées dans le venv uv.
  - Kernel Jupyter présent dans la liste `jupyter kernelspec list`.
  - Intégrité des 7 documents PDF dans `data/corpus/`.

