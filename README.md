# CourseScope (🚧 en cours de travaux)

## Infos générales

CourseScope est une application web locale pour analyser des traces running **GPX/FIT**.

L'objectif: importer une activite (ou une trace), puis explorer rapidement les metriques, cartes et graphiques (allure, pente, denivele, zones, splits, best efforts), avec un mode **theorique** pour estimer un temps/allure sur un parcours.

Le projet est compose d'un **frontend Next.js** (UI) et d'une **API FastAPI** (backend). En dev, le frontend parle au backend via un proxy `/api/*` (rewrite Next.js) pour eviter les problemes de CORS.

## 🚀 Démarrage rapide

### 1) Lancer en mode développement (recommandé)

Prérequis:
- Python 3.11+
- Node.js 20+ (22 recommande pour eviter certains warnings de dependances)

```bash
# Windows
./run_win.bat

# Linux/macOS
./run_linux.sh --dev
```

URLs (dev):
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

### 2) Lancer via Docker (image unique)

L'image officielle est publiee sur GHCR.

```bash
docker pull ghcr.io/kolokolone/coursescope:main
docker run --rm -p 3000:3000 -v "${PWD}/data:/data" ghcr.io/kolokolone/coursescope:main
```

URLs (docker):
- UI: http://localhost:3000

Note: dans cette image, le backend tourne dans le conteneur sur `127.0.0.1:8000` et n'est pas expose directement. L'UI consomme l'API via le proxy `/api/*`.

### 3) Exemple de `docker-compose.yml`

Le repo ne fournit pas encore de `docker-compose.yml`, mais voici un exemple minimal fonctionnel:

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

Demarrage:
```bash
docker compose up -d
docker compose logs -f
```

## 🏃 Fonctionnalités

- Import GPX/FIT via l'UI (drag & drop) et gestion de l'historique des activites
- Analyse **reelle**: metriques type Garmin, zones (FC/allure/puissance), series, carte, highlights
- Analyse **theorique**: estimation temps/allure sur un parcours avec modele de pente, VMA, et graphiques dedies
- Graphiques principaux:
  - Allure vs distance (theorique)
  - Temps par allure (bins de 15s/km)
  - Temps par % de pente (bins de 0.5%, pente clippee a [-20%, 20%])
  - Denivele (profil altitude vs distance)
  - Allure vs pente (pace-vs-grade) calcule cote backend
- Gestion des **traces** (liste, upload, rename, suppression, ouverture)
- Integration Garmin (connexion, sync, status, reset) + stockage local des tokens
- Parametres perso: VMA, HR max (detecte/manual), options de persistance
- Progress / historique: endpoints pour verification, series agregees, best efforts, tagging, etc.

## 📁 Architecture du projet

```text
CourseScope/
├── Dockerfile
├── run_win.bat
├── run_linux.sh
├── requirements.txt
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   ├── core/
│   ├── services/
│   ├── storage/
│   └── db/
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   └── src/
└── tests/
```

Donnees runtime (par defaut): `./data/`
- Logs backend: `data/logs/backend_<timestamp>.log`
- Activites/traces/tokens (selon options): `data/activities/`, `data/traces/`, `data/integrations/garmin/`

## 📡 Endpoints API

Regle de compatibilite: les routes existent en **/xxx** et aussi en **/api/xxx**.

Principaux endpoints:

- Sante
  - `GET /health`

- Activites
  - `POST /activity/load` (upload GPX/FIT)
  - `GET /activities`
  - `DELETE /activity/{id}`
  - `DELETE /activities`

- Analyses
  - `GET /activity/{id}/real`
  - `GET /activity/{id}/theoretical`
  - `GET /activity/{id}/pace-vs-grade`
  - `GET /activity/{id}/series`
  - `GET /activity/{id}/series/{name}`
  - `GET /activity/{id}/map`

- Traces
  - `GET /traces`
  - `POST /traces/upload`
  - `DELETE /traces`
  - `PATCH /traces/{id}` (rename)
  - `DELETE /traces/{id}`
  - `POST /traces/{id}/open`
  - `GET /activity/{id}/trace-status`
  - `POST /activity/{id}/trace-save`

- Garmin
  - `POST /integrations/garmin/connect`
  - `POST /integrations/garmin/sync`
  - `POST /integrations/garmin/reset`
  - `GET /integrations/garmin/status`

- Progress
  - `POST /progress/verify`
  - `GET /progress/verify-status`
  - `GET /progress/activities`
  - `GET /progress/series`
  - `GET /progress/best-efforts`
  - `GET /progress/hr-at-pace`
  - `GET /progress/pace-at-hr`
  - `GET /progress/session-taxonomy`
  - `POST /progress/tags`
  - `GET /progress/pace-hr-waterfall`

- Settings
  - `GET /settings/personal`
  - `PATCH /settings/personal`
  - `GET /settings/personal/hr-max-detected`

## 🧪 Tests

Backend:
```bash
python -m compileall backend
python -m pytest tests/pytest/
python -m pytest tests/unit/
```

Frontend:
```bash
cd frontend
npm test
npm run build
```

## 📋 Dépendances

Python (voir `requirements.txt`):
- parsing/compute: `gpxpy`, `fitparse`, `pandas`, `numpy`, `plotly`
- API: `fastapi`, `uvicorn[standard]`, `python-multipart`, `pydantic`, `httpx`
- data: `pyarrow`
- integrations/DB: `garminconnect`, `garth`, `SQLAlchemy`, `psycopg[binary]`

Frontend (voir `frontend/package.json`):
- Next.js 16, React 19, Tailwind 4, Recharts, React Query, Leaflet

CI / Docker:
- Image unique publiee sur GHCR: `ghcr.io/kolokolone/coursescope:main`

---

Changelog: voir `CHANGELOG.md`.
