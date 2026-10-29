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


## Séance 1 : Extraction PDF et Découpage (Chunking)
- **Date** : 29/10/2026
- **Outil d'IA** : Antigravity (Modèle Gemini 3.8 Flash High)
- **Objectifs de l'étape** :
  - Extraction de texte avec `pdfplumber` sur les 7 PDF du corpus `data/corpus/`.
  - Extraction automatique et générique des métadonnées du tableau officiel en page 1 (référence, date, type, version, statut).
  - Filtrage des en-têtes répétés ("École d'Ingénieurs Hélianthe...") et pieds de page ("Document fictif à usage pédagogique... page X").
  - Préservation du contexte relationnel des tableaux (chaque ligne liée explicitement à ses en-têtes de colonne au format `Colonne : Valeur — Colonne : Valeur`).
  - Développement de 2 stratégies manuelles de découpage : taille fixe avec chevauchement (`chunk_fixed`, 500 / 100) et structurelle (`chunk_structural`, détection des Articles, Titres, questions FAQ et sections).
  - Génération du fichier intermédiaire `chunks.json` (111 fragments structurels riches).
  - Intégration dans le notebook `notebooks/rag_eih.ipynb` avec cellules Markdown de justification pédagogique.
- **Vérifications effectuées** :
  - Exécution complète des cellules S1 du notebook de bout en bout.
  - Inspection de `chunks.json` : présence des 7 documents, pagination exacte, et capture des modifications de la Note de service n° 2026-14.
