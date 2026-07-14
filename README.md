# CourseScope

Application web locale pour analyser des activités running **GPX/FIT** et préparer une course à partir d'une trace théorique indépendante.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.2.7-0f172a.svg)](VERSION)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)

## Pourquoi ?

Importer une activité réelle pour l'analyser, ou une trace distincte pour préparer une course avec objectifs, scénarios, pauses, passages et stratégie.

Le projet est composé d'un **frontend Next.js** (UI) et d'une **API FastAPI** (backend). En dev, le frontend parle au backend via un proxy `/api/*` (rewrite Next.js) pour éviter les problèmes de CORS.

## Fonctionnalités principales

| Fonctionnalité | Statut | Description |
|---|---|---|
| Import GPX/FIT | ✅ | Flux activité réelle et flux trace théorique strictement séparés |
| Analyse réelle | ✅ | Métriques type Garmin : zones FC/allure/puissance, séries, carte, highlights |
| Préparation de course | ✅ | Profil robuste, Minetti, objectifs allure/temps/effort, pauses et scénarios persistés |
| Graphiques | ✅ | Allure vs distance, temps par allure, temps par pente, dénivelé, allure vs pente |
| Gestion des traces | ✅ | Import partagé, Parquet prioritaire, renommage, suppression et ouverture directe par `trace_id` |
| Intégration Garmin | ✅ | Connexion, sync, status, reset — stockage local des tokens |
| Progression | ✅ | Dashboard multi-activités : volume, TRIMP, charge, best efforts, EF, découplage, HR@pace, waterfall 3D, session taxonomy, intensity distribution, long run dose, VAM trend |
| Objectifs | ✅ | CRUD courses à venir, timeline, calendrier, carte Leaflet |
| Paramètres | ✅ | VMA, FC max, détection auto, maintenance, indexation |
| Cache et indexation | ✅ | Indexation analytique SQLite fast/slow, cache LRU, pas de recompute inutile |
| Docker | ✅ | Image unique sur GHCR : `ghcr.io/kolokolone/coursescope:main` |

## Démarrage rapide

### Prérequis
- Python 3.13+
- Node.js 22+

### Lancement en développement

```bash
# Windows
./run_win.bat

# Linux/macOS
./run_linux.sh --dev
```

URLs (dev) :
- Frontend : http://localhost:3000
- API : http://localhost:8000
- API docs (Swagger) : http://localhost:8000/docs

### Lancement via Docker

```bash
docker pull ghcr.io/kolokolone/coursescope:main
docker run --rm -p 3000:3000 -v "${PWD}/data:/data" ghcr.io/kolokolone/coursescope:main
```

Exemple `docker-compose.yml` :

```yaml
services:
  coursescope:
    image: ghcr.io/kolokolone/coursescope:main
    container_name: coursescope
    ports:
      - "3000:3000"
    environment:
      COURSESCOPE_DATA_DIR: /data
    volumes:
      - ./data:/data
    restart: unless-stopped
```

## Configuration

| Variable | Obligatoire | Description |
|---|---|---|
| `COURSESCOPE_DATA_DIR` | Non | Répertoire des données runtime (défaut : `./data`) |
| `COURSESCOPE_DB_URL` | Non | URL SQLite (défaut : `sqlite:///data/coursescope.sqlite`) |
| `COURSESCOPE_RELOAD` | Non | Active le reload uvicorn (défaut : désactivé) |
| `COURSESCOPE_PRO_PACE_VS_GRADE_PATH` | Non | Chemin alternatif vers la table de référence pro |

## Architecture

```text
CourseScope/
├── backend/                  # API FastAPI + logique métier
│   ├── api/                  # Routes REST FastAPI
│   │   ├── main.py           # App factory, CORS, lifespan
│   │   ├── schemas.py        # Modèles Pydantic (request/response)
│   │   └── routes/           # Handlers : activities, analysis, traces,
│   │                           progress, goals, settings, garmin, maps,
│   │                           series, geo
│   ├── core/                 # Moteur d'analyse (parsing GPX/FIT, calculs)
│   ├── services/             # Orchestration (cache, sérialisation, analyse)
│   ├── storage/              # Persistance fichiers (parquet + metadata)
│   ├── db/                   # Accès SQLite (modèles, repositories)
│   ├── progress/             # Indexation analytique fast/slow
│   ├── registry/             # Registre des séries (downsampling LTTB)
│   ├── integrations/garmin/  # Client Garmin Connect
│   └── config.py             # Résolution des chemins
├── frontend/                 # UI Next.js 16 + React 19 + Tailwind 4
│   └── src/
│       ├── app/              # Pages (App Router) : home, activities,
│       │                       progress, goals, traces, settings
│       ├── components/       # Composants : layout, charts, maps,
│       │                       analysis, trace-planning, metrics, features
│       ├── hooks/            # React Query hooks (useActivity, useProgress, ...)
│       ├── lib/              # API client, metrics registry, formatters, types
│       └── store/            # Zustand (uiPrefsStore)
├── agents/                   # Configuration des agents de développement
│   ├── AGENTS.md             # Règles globales et workflow
│   ├── agent-brainstorm.md   # Agent d'analyse et planification
│   ├── agent-dev.md          # Agent d'implémentation
│   ├── agent-review.md       # Agent d'audit
│   └── modifications.txt     # Entrée utilisateur du workflow
├── docs/                     # Documentation technique
│   ├── metrics_catalog.md    # Catalogue complet des métriques API
│   ├── design.md             # Système de design (couleurs, typo, composants)
│   ├── style-frontend-ui.md  # Guide de style UI normatif
│   ├── indexation.md         # Architecture d'indexation fast/slow
│   ├── progression.md        # Spécification de la page Progression
│   ├── pace_vs_grade.md      # Algorithme allure vs pente
│   ├── climbs.md             # Algorithme de détection des montées
│   ├── documentation_update_runbook.md  # Procédure de mise à jour docs
│   ├── race-planning.md      # Traces et préparation de course
│   └── ...
├── tests/                    # Tests backend (pytest unit + smoke)
├── scripts/                  # Scripts CLI (indexation)
├── data/                     # Données runtime (non versionné)
├── Dockerfile                # Image unique multi-stage
├── requirements.txt          # Dépendances Python
├── run_win.bat               # Lanceur Windows
├── run_linux.sh              # Lanceur Linux/macOS
└── CHANGELOG.md              # Historique des versions
```

## Backend

- **Framework** : FastAPI avec uvicorn
- **Parsing** : gpxpy (GPX), fitparse (FIT) → DataFrame pandas canonique versionné
- **Analyses** : calculs de pente, GAP, zones FC/allure/puissance, splits, best efforts, montées, prédictions de performance, pacing, TRIMP, découplage cardiaque
- **Stockage** : fichiers parquet + métadonnées JSON, index SQLite pour la progression
- **Indexation** : système fast/slow avec fingerprint et versioning des métriques
- **Séries** : registre centralisé avec downsampling LTTB, 10+ séries (pace, HR, elevation, grade, power, cadence...)

## Frontend

- **Framework** : Next.js 16 (App Router) + React 19 + TypeScript
- **Styling** : Tailwind CSS 4 avec design tokens (Space Grotesk, JetBrains Mono)
- **Graphiques** : Recharts 3.7 + react-three-fiber (waterfall 3D)
- **Cartes** : Leaflet + react-leaflet
- **State** : TanStack React Query (server) + Zustand (client, localStorage)
- **Composants** : shadcn/ui adapté (Card, Button via CVA)
- **Proxy API** : rewrite Next.js `/api/*` → `http://127.0.0.1:8000/*`

## Endpoints API

Les endpoints backend sont servis en `/xxx`; le frontend les atteint également via son proxy `/api/xxx`.

Documentation complète : voir [docs/metrics_catalog.md](docs/metrics_catalog.md) et Swagger (`/docs`).

Principaux groupes :
- **Activités** : upload, list, delete, rename
- **Analyse réelle** : real, pace-vs-grade, real-bins
- **Séries** : données par série nommée, liste des séries disponibles
- **Cartes** : bbox, polyligne, marqueurs
- **Traces** : import, détail direct, plan-preview, plans, scénarios, pauses, calibration et comparaison
- **Progression** : indexation, activités, séries, best efforts, HR@pace, pace@HR, waterfall, training load, calendrier
- **Objectifs** : CRUD courses
- **Paramètres** : VMA, FC max personnelle et détectée
- **Garmin** : connect, sync, reset, status, credentials
- **Géo** : autocomplétion de villes

## Métriques

Le catalogue complet des métriques exposées par l'API est documenté dans [docs/metrics_catalog.md](docs/metrics_catalog.md).

Les métriques sont organisées par endpoint :
- **Activité réelle** : summary, cardio, Garmin summary, highlights, zones, best efforts, splits, pacing, cadence, power, running dynamics, training load, climbs
- **Trace théorique** : profil Minetti, passages, splits, ascensions, histogrammes, alertes et qualité
- **Progression** : activités indexées, séries agrégées, best efforts timeline, HR@pace, pace@HR, waterfall 3D, training load, calendrier

## Développement

### Backend

```bash
# Vérification syntaxe
python -m compileall backend

# Tests unitaires
python -m pytest tests/unit/

# Tests d'intégration
python -m pytest tests/pytest/

# Smoke test
python tests/smoke_test.py

# Migration de la préparation de course
cd backend
python -m db.migrations.run
```

### Frontend

```bash
cd frontend
npm test           # Vitest
npm run build      # Build production
npm run lint       # ESLint
```

## Déploiement

Image unique multi-stage publiée sur GHCR. Le build compile le frontend Next.js puis assemble backend Python + frontend statique dans une image `python:3.13-slim-bookworm` avec Node.js 22.

```bash
docker build -t coursescope .
docker run --rm -p 3000:3000 -v ./data:/data coursescope
```

## Sécurité

- Ne jamais commiter de tokens, credentials ou fichiers `data/integrations/garmin/`
- Les tokens Garmin sont stockés localement dans `data/` (non versionné)
- Pas d'authentification multi-utilisateur (application locale)

## Limitations connues

- Application mono-utilisateur, conçue pour un usage local
- Pas de dark mode (light mode uniquement, optimisé pour la lisibilité des graphiques)
- L'indexation SQLite est optimisée pour < 10 000 activités
- La météo externe n'est pas configurée par défaut ; le pipeline fonctionne sans fournisseur ou avec des hypothèses de scénario
- Pas de support multi-sport au-delà du running et trail running

## Ressources complémentaires

| Document | Description |
|---|---|
| [docs/metrics_catalog.md](docs/metrics_catalog.md) | Catalogue complet des métriques API |
| [docs/design.md](docs/design.md) | Système de design complet |
| [docs/style-frontend-ui.md](docs/style-frontend-ui.md) | Guide de style UI normatif |
| [docs/indexation.md](docs/indexation.md) | Architecture d'indexation |
| [docs/progression.md](docs/progression.md) | Spécification Progression |
| [docs/race-planning.md](docs/race-planning.md) | Architecture, API et calculs de préparation de course |
| [agents/AGENTS.md](agents/AGENTS.md) | Règles globales pour les agents |
| [CHANGELOG.md](CHANGELOG.md) | Historique des versions |

## Licence

MIT — voir [LICENSE](LICENSE).

---

Stack : **Python 3.13+ / FastAPI / pandas** + **Next.js 16 / React 19 / Tailwind 4 / Recharts / Leaflet**
