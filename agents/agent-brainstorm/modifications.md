# CourseScope - Modifications (agent-brainstorm)

Repo local: `C:\Users\domin\Documents\Python Scripts\CourseScope`
Repo github: `https://github.com/kolokolone/CourseScope`

Contrainte (phase brainstorm): ne pas toucher au code applicatif ici; decrire les modifications a faire dans `docs/modifications.txt` et donner des details d'implementation coherents avec le code existant.

Source unique (scope): `docs/modifications.txt`.

---

## 0) Perimetre et principes

- Objectif: deploiement le plus simple possible sur Dockge (LAN) via `docker pull ghcr.io/kolokolone/coursescope:main`.
- Cible: 1 seule image Docker qui lance backend + frontend automatiquement (multi-process dans un conteneur).
- Ne pas casser Windows local: l'utilisateur lance toujours `start_backend.bat` puis `start_frontend.bat`.
- En prod Docker: ne pas exposer l'API (8000) au LAN; tout passe par le proxy Next `/api/*`.

---

## 1) Image unique: comment lancer API + WEB automatiquement

### 1.1 Etat actuel (constats verifies dans le repo)

Windows local:
- `start_backend.bat` lance uvicorn sur `127.0.0.1:8000`.
- `start_frontend.bat` lance `npm run dev` sur 3000.

Linux local:
- `run_linux.sh` existe mais est dev-only:
  - cree une venv, installe deps, lance `uvicorn --reload --host 0.0.0.0`, puis `npm run dev`.

Proxy frontend:
- `frontend/next.config.ts` rewrite `/api/:path*` vers `http://127.0.0.1:8000/:path*`.
- Avec une image unique, ce hardcode est OK (API et web dans le meme conteneur).

Piege majeur a corriger:
- `frontend/.env.local` force `NEXT_PUBLIC_API_URL=http://localhost:8000`.
  - En prod, ca casse (le navigateur du client LAN appelle SON localhost).

### 1.2 Choix technique recommande: re-utiliser `run_linux.sh` comme entrypoint Docker

Pourquoi:
- Tu as deja un launcher "unifie" pour Linux.
- Il gere deja un `trap` de nettoyage.
- On peut le rendre dual-mode: dev (actuel) / docker (nouveau), sans casser l'usage existant.

Changement a faire:
- Modifier `run_linux.sh` pour ajouter un mode `--docker`.

Comportement attendu en mode `--docker`:
- Ne pas creer de venv et ne pas installer de dependances au runtime.
- Lancer uvicorn en background:
  - `python3 -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000`
- Optionnel: attendre que `/health` reponde (poll via python pour eviter curl).
- Lancer Next en foreground:
  - `cd frontend && npm run start -- -H 0.0.0.0 -p 3000`
- Garder un `trap`/cleanup qui stoppe l'API quand le web s'arrete.

Gestion signaux:
- Installer `tini` dans l'image et l'utiliser comme `ENTRYPOINT` pour une gestion propre de SIGTERM.

### 1.3 Fichiers a creer/modifier pour Docker

Fichiers a creer:
- `.dockerignore` (racine)
- `Dockerfile` (racine) (image unique)
- `.github/workflows/docker-image.yml` (nécessaire pour GHCR)

Fichiers a modifier:
- `run_linux.sh` (ajout mode `--docker`)
- `frontend/.env.local` (retirer du repo; remplacer par `frontend/.env.example`)

### 1.4 Dockerfile (points d'attention)

- Build frontend en multi-stage (npm ci + npm run build) et copier le resultat dans l'image runtime.
- Installer Python + pip et deps `requirements.txt`.
- Installer `tini`.
- Copier `run_linux.sh` dans l'image, corriger les fins de ligne Windows (CRLF) au build:
  - `sed -i 's/\r$//' /app/run_linux.sh`
- `CMD ["/app/run_linux.sh", "--docker"]`.

### 1.5 Compose Dockge (service unique)

- Service unique `coursescope`.
- Exposer `3000:3000`.
- Volume persistant sur `/data` + `COURSESCOPE_DATA_DIR=/data`.
- Ne pas definir `NEXT_PUBLIC_API_URL`.

---

## 2) Persistance (volume Docker)

Le backend ecrit sous `COURSESCOPE_DATA_DIR`:
- `activities/`, `traces/`, `integrations/garmin/tokens/`, `logs/`, `coursescope.sqlite`.

Donc le compose doit monter un volume sur `/data`.

---

## 3) GHCR (une seule image)

But:
- Publier `ghcr.io/kolokolone/coursescope:main`.

Points importants:
- `GITHUB_TOKEN` + `packages: write` dans le workflow.
- Sur le serveur: `docker login ghcr.io` avec un PAT `read:packages` si l'image est privee.
- me dire comment faire pour qu'il soit public (mon depot github est déjà public)

---

## 4) Sections non impactees

Les demandes UI (trace gpx, graphiques, etc.) restent telles que definies dans `docs/modifications.txt`.
