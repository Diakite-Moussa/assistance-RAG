# Assistant Scolarité RAG — École d'Ingénieurs Hélianthe (EIH)

Application web de questions-réponses qui répond aux étudiants de l'École d'Ingénieurs Hélianthe (école fictive) **uniquement à partir de ses 7 documents officiels**. Chaque réponse cite ses sources (`[1]`, `[2]`…) et, quand l'information n'existe pas dans le corpus, le système répond exactement :

> Je ne trouve pas cette information dans les documents de l'École.

Projet réalisé dans le cadre du module **Retrieval-Augmented Generation (RAG)** — Université Mundiapolis, 3ACINFO (Pr. Habib Ayad).

---

## 1. Architecture

```
Ingestion (une fois)
  PDF ──► extraction (pdfplumber) ──► découpage (fixe | structurel) ──► embeddings (e5) ──► ChromaDB (disque)

Question (à chaque requête)
  Angular ──► POST /api/ask ──► recherche top-k ──► contrôle du seuil ──► ajout des documents modificatifs
          ◄── réponse + sources ◄── contrôle des citations ◄── LLM (Groq) ◄── prompt
```

| Couche | Choix |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, gestionnaire `uv` |
| Extraction | `pdfplumber` (texte, tableaux, métadonnées de la page 1) |
| Embeddings | `intfloat/multilingual-e5-small` (préfixes `passage:` / `query:`) |
| Base vectorielle | ChromaDB persistante (`chroma_db/`), distance cosinus, une collection par stratégie de découpage |
| LLM | API Groq, modèle `openai/gpt-oss-120b`, température 0, clé dans `.env` |
| Frontend | Angular (composants standalone, `RagApiService`), TypeScript |
| Tests | pytest (faux embedder et faux LLM, aucun appel réseau) |

Le découpage et le prompt sont écrits à la main (ni LangChain, ni LlamaIndex).

---

## 2. Prérequis

- Python 3.11 ou plus et [uv](https://github.com/astral-sh/uv)
- Node.js et npm (pour le frontend Angular)
- Une clé d'API Groq (gratuite) : <https://console.groq.com>
- Connexion internet au premier lancement : le modèle d'embedding (plusieurs centaines de Mo) est téléchargé depuis Hugging Face. Le message sur `HF_TOKEN` est un simple avertissement, le token est facultatif.

---

## 3. Installation

```powershell
# 1. Variables d'environnement
Copy-Item .env.example .env        # Linux/macOS : cp .env.example .env
# puis renseigner GROQ_API_KEY dans .env

# 2. Dépendances Python (crée .venv)
uv sync

# 3. Dépendances du frontend
cd frontend
npm install
cd ..
```

Le fichier `.env` est ignoré par Git. **Ne jamais committer la clé.** Aucune clé n'est présente côté navigateur : seul le backend appelle le LLM.

### Variables d'environnement (`.env`)

| Variable | Défaut | Rôle |
|---|---|---|
| `GROQ_API_KEY` | *(vide)* | Clé de l'API Groq (obligatoire pour `/api/ask`) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Modèle de génération |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Point d'accès compatible OpenAI (facultatif) |
| `LLM_TIMEOUT` | `60` | Délai maximal d'un appel LLM (secondes) |
| `EMBEDDING_MODEL_NAME` | `intfloat/multilingual-e5-small` | Modèle d'embedding |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | Dossier de la base vectorielle |
| `CHROMA_COLLECTION_NAME` | `eih_scolarite` | Préfixe des collections (suffixe : `_structural` ou `_fixed`) |
| `RETRIEVAL_TOP_K` | `5` | Nombre de fragments retrouvés par défaut |
| `SCORE_THRESHOLD` | `0.83` | Seuil de refus : si le meilleur score cosinus est inférieur, l'API refuse sans appeler le LLM |
| `CHUNK_STRATEGY` | `structural` | Stratégie par défaut : `structural` ou `fixed` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `100` | Paramètres du découpage fixe |
| `MAX_SECTION_CHARS` | `900` | Taille maximale d'un fragment structurel avant coupe |
| `CORS_ORIGINS` | `http://localhost:4200` | Origines autorisées (séparées par des virgules) |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Présentes dans `.env.example` mais **non lues par le code** : utiliser `--host` et `--port` d'uvicorn |

Le seuil de 0,83 a été calibré avec `eval/calibrate_threshold.py` : les questions hors corpus obtiennent au plus 0,81, les questions du corpus au moins 0,86. À recalibrer si le corpus, le modèle d'embedding ou la stratégie changent.

L'URL de l'API côté frontend se règle dans `frontend/src/environments/environment.ts` (`apiUrl`, par défaut `http://localhost:8000/api`).

---

## 4. Lancement

### 4.1 Backend

Depuis la racine du projet :

```powershell
uv run uvicorn app.main:app --reload --app-dir backend
```

- API : <http://localhost:8000/api>
- Documentation interactive (Swagger) : <http://localhost:8000/docs>

### 4.2 Indexation (premier lancement)

La base `chroma_db/` n'est pas versionnée : il faut l'indexer une fois. Dans `/docs`, exécuter `POST /api/ingest` avec `{"strategy": "structural"}`, ou :

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/ingest `
  -ContentType 'application/json; charset=utf-8' -Body '{"strategy":"structural"}'
```

L'ingestion est **idempotente** : l'identifiant d'un fragment est stable (`REFERENCE:stratégie:index`), les fragments sont écrits par *upsert* et ceux devenus obsolètes sont supprimés. La relancer ne crée pas de doublons. Pour comparer les deux stratégies, indexer aussi `{"strategy": "fixed"}`.

Pour inspecter les fragments sans indexer (depuis `backend/`) :

```powershell
cd backend
uv run python -m app.build_chunks --strategy structural   # écrit data/chunks_structural.json
```

### 4.3 Frontend

```powershell
cd frontend
npm start        # ng serve → http://localhost:4200
```

Écrans : **Conversation** (citations cliquables, panneau des sources, exemples de questions), **Documents** (liste issue de `GET /api/documents`), **Recherche** (mode débogage : fragments bruts et scores, sans LLM). `top_k` et le filtre par type de document sont réglables.

---

## 5. API

Toutes les routes sont préfixées par `/api`.

| Route | Rôle | Erreurs |
|---|---|---|
| `GET /api/health` | État du service, stratégie active, nombre de fragments | 503 si la base est indisponible |
| `POST /api/ingest` | (Ré)indexation : `strategy`, `chunk_size`, `chunk_overlap`, `max_section_chars` | 422 si paramètres invalides (ex. chevauchement ≥ taille) |
| `GET /api/documents` | Documents indexés, métadonnées, nombre de fragments | — |
| `POST /api/search` | Recherche seule, sans LLM : fragments et scores | 422 si la question est vide |
| `POST /api/ask` | Recherche puis génération, avec citations | 422 ; 502 si le LLM ne répond pas |

Exemple :

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/ask `
  -ContentType 'application/json; charset=utf-8' `
  -Body '{"question":"Quelle est la durée minimale du PFE ?","top_k":5,"filters":{"type":null}}'
```

Réponse :

```json
{
  "answer": "La durée minimale du PFE est de 18 semaines … [1][5]",
  "found": true,
  "sources": [{"id": 1, "chunk_id": "…", "file": "…", "reference": "EIH-DE-NS-2026-14",
               "date": "2026-10-05", "page": 1, "section": "…", "excerpt": "…", "score": 0.92}],
  "invalid_citations": [],
  "latency_ms": 800
}
```

Hors corpus : `found` vaut `false`, `answer` contient la phrase de refus et `sources` est une liste vide. Le filtre `filters.type` accepte les types de documents du corpus (« Règlement officiel », « Guide pratique », « Charte et procédure », « Calendrier officiel », « Guide d'information », « FAQ (questions-réponses) », « Note de service (texte modificatif) »).

---

## 6. Tests

```powershell
uv run pytest
```

Les tests n'utilisent ni le vrai modèle d'embedding ni le réseau : un faux embedder et un faux LLM (`httpx.MockTransport` pour le client Groq) rendent la suite rapide et déterministe. Ils couvrent notamment :

- le **découpage** : métadonnées complètes sur chaque fragment, en-têtes de tableaux conservés, taille et chevauchement du découpage fixe, identifiants stables ;
- l'**indexation** : idempotence, suppression des fragments obsolètes, tri des scores, filtre par type ;
- le **refus hors corpus** : une question hors sujet est refusée par le seuil sans appeler le LLM ;
- les **contrôles de citations** : citations hors bornes signalées, réponse sans citation valide traitée comme un refus, crochets pleine chasse `【1】` normalisés ;
- l'**API** : codes 422, 502 et 503, forme exacte de la réponse de `/api/ask` ;
- le **client LLM** : format OpenAI, erreurs 401/429/500, la clé n'apparaît jamais dans un message d'erreur.

---

## 7. Évaluation

Jeu de test : `eval/questions.json` — 36 questions (26 dans le corpus, 4 hors corpus, 6 sur un sujet du corpus dont la réponse précise est absente). Les réponses attendues et les fragments justificatifs sont rédigés à partir du texte extrait des documents.

```powershell
uv run python eval/run_eval.py                                        # recherche seule, fixe vs structurel (sans LLM)
uv run python eval/run_eval.py --strategies structural --llm          # bout en bout (appelle Groq)
uv run python eval/run_eval.py --strategies structural fixed --ks 1 3 5 8
uv run python eval/calibrate_threshold.py                             # calibration du seuil de refus
```

Chaque exécution écrit un rapport détaillé (réponses du LLM comprises) dans `eval/results/`. Métriques : any@k, all@k, MRR, faux refus du seuil, refus corrects, décision trouvé/refus, mots-clés attendus, citations valides, citation du document modificatif, latence.

Dernière évaluation (30/10/2026, stratégie structurelle, k = 5, `openai/gpt-oss-120b`) :

| Mesure | Résultat |
|---|---|
| any@5 / MRR (recherche) | 25/26 (96 %) / 0,821 |
| Décision trouvé/refus correcte | 34/36 (94 %) |
| Refus corrects (hors corpus + même sujet sans réponse) | 10/10 |
| Document modificatif cité quand il le faut | 6/6 |
| Latence moyenne | 691 ms |

Le détail, la comparaison des stratégies et l'analyse des échecs sont dans le rapport.

---

## 8. Choix techniques

- **Extraction.** Les métadonnées (référence, type, date, version, statut) sont lues dans le tableau de la page 1. Les en-têtes et pieds de page répétés sont filtrés. Chaque ligne de tableau est transformée en `En-tête : valeur — En-tête : valeur`, ce qui garde le lien entre la ligne et ses colonnes (essentiel pour le calendrier et la charte de mobilité).
- **Découpage.** Deux stratégies écrites à la main : fenêtre de 500 caractères avec 100 de chevauchement (coupe aux espaces), et découpage structurel (un fragment par article, question-réponse, rubrique ou bloc de tableau, titre répété si la section est coupée). Chaque fragment porte : identifiant, fichier, référence, type, date, version, statut, page, section.
- **Texte vectorisé.** Titre du document + section + contenu, pour que « Article 14 — Session de rattrapage » pèse dans la similarité.
- **Versions sans règle écrite en dur.** Un document dont le statut contient « modifie » et cite une autre référence est marqué `amends`. Après la recherche, si un fragment vient d'un document modifié, les fragments pertinents du document modificatif sont ajoutés au contexte, et le prompt présente la référence, la date et le statut de chaque fragment avec la mention « CE DOCUMENT MODIFIE … ».
- **Prompt.** Réponse uniquement à partir des fragments, citation de chaque affirmation, refus exact, priorité au document modificatif, calcul détaillé à partir des chiffres fournis.
- **Contrôles côté code.** (1) Meilleur score < seuil : refus sans appeler le LLM. (2) Tout numéro cité doit correspondre à un fragment fourni, sinon il est signalé dans `invalid_citations`. (3) Une réponse sans aucune citation valide est traitée comme un refus. Le refus est toujours renvoyé sous sa forme exacte.

---

## 9. Structure du dépôt

```
backend/app/     config, extract, chunking, embeddings, indexing, prompt, llm, rag, schemas, main
backend/tests/   tests pytest
data/corpus/     les 7 PDF (non modifiés)
eval/            questions.json, run_eval.py, calibrate_threshold.py, results/
frontend/        application Angular
notebooks/       rag_eih.ipynb (développement par séances)
AI_LOG.md        journal d'utilisation de l'IA générative
```

---

## 10. Limites connues

- Les questions dont la réponse se trouve dans une ligne noyée au milieu d'un gros bloc de tableau peuvent échapper à la recherche (exemple : les dates des soutenances de stage technique dans le calendrier, question Q18).
- Un cas de calcul à plusieurs règles voisines (Q05, plafond du rattrapage) est parfois refusé par le LLM à tort.
- Le seuil de refus est calibré sur peu de questions hors corpus et ne peut pas refuser une question sur un sujet présent dans le corpus : c'est le prompt qui s'en charge.
- Chaque question est traitée indépendamment : pas de mémoire de conversation.
- `POST /api/ingest` n'est pas protégé : à restreindre avant tout déploiement hors poste local.

---

## 11. Usage de l'IA générative

Les outils utilisés, les parties concernées et les vérifications effectuées sont déclarés dans `AI_LOG.md` et dans l'annexe du rapport.