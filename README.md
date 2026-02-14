# CourseScope

CourseScope est une application web locale pour analyser des traces running GPX/FIT.

## Prerequis

- Python 3.11+
- Node.js (npm)

## 🚀 Démarrage rapide

```bash
# Windows
./run_win.bat

# Linux/macOS
./run_linux.sh
```

URLs:
- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs: /docs)

Pages:
- Accueil: http://localhost:3000
- Parametres: http://localhost:3000/settings
- Historique des activites: http://localhost:3000/activities

Note Windows:
- Le premier lancement peut prendre du temps (installation `npm` dans `frontend/`).
- Les lancements suivants sont rapides (si `frontend/node_modules/` existe, l'installation est skip).
- En dev, le frontend passe par le proxy Next.js (`/api/*`) par defaut (recommande) pour eviter les problemes CORS/URL.

## Allure vs pente (pace_vs_grade)

Le graphique "Allure en fonction de la pente" est calcule cote backend via `GET /activity/{id}/pace-vs-grade`.

Definition (v1.1.44+):
- "Moving" = temps en mouvement (incluant marche), pauses/arrêts exclus via `compute_moving_mask` (pause>=5s).
- Binning pente: grade clippe a [-20, +20], bins fixes de 0.5% (bornes incluses).
- Agrégats: statistiques pondérées par le temps (`delta_time_s`) + gestion robuste des outliers par bin.

Details: `docs/pace_vs_grade.md`

## Montees detectees (climbs)

La section "Montees detectees" (categorie Climbs) est calculee cote backend via `compute_climbs`.

Details: `docs/climbs.md`

## CI (local)

```bash
python dev/scripts/ci_pipeline.py
```

## 📁 Architecture du projet

```
CourseScope/
├── run_win.bat / run_linux.sh     # Scripts de lancement rapide
├── requirements.txt               # Dépendances Python
├── backend/
│   ├── api/                     # API FastAPI
│   │   ├── main.py             # Serveur FastAPI + CORS + logs
│   │   └── routes/
│   │       ├── activities.py    # POST /activity/load (upload)
│   │       ├── analysis.py      # Analyses real/theoretical
│   │       ├── garmin_integration.py # Garmin Connect: connect/sync/status
│   │       ├── series.py       # Séries de données
│   │       └── maps.py         # Données cartographiques
│   ├── core/                     # Logique métier pure Python
│   │   ├── gpx_loader.py       # Parser GPX → DataFrame
│   │   ├── fit_loader.py       # Parser FIT → DataFrame  
│   │   ├── contracts/          # Validation DataFrame canonique
│   │   ├── metrics.py          # Calculs style Garmin
│   │   ├── theoretical_model.py # Prédictions temps/allure
│   │   └── ...
│   ├── services/                 # Orchestration backend
│   │   ├── activity_service.py  # Chargement + validation
│   │   ├── analysis_service.py  # Entry points API
│   │   ├── cache.py           # Cache portable
│   │   └── serialization.py   # Conversion JSON
│   ├── storage/                  # Persistance locale
│   ├── db/                       # Index DB (PostgreSQL-ready)
│   └── integrations/             # Integrations externes (Garmin)
├── frontend/
│   ├── src/
│   │   ├── lib/api.ts          # Client API avec proxy
│   │   ├── components/upload/    # Upload dropzone
│   │   └── app/               # Pages Next.js
│   └── next.config.ts           # Configuration proxy API
└── tests/                       # Tests unitaires + pytest
```

## 🔌 Configuration API (v1.1.33)

### Stratégie de communication
- **Développement local (par défaut)** : Proxy Next.js (`/api/*` → `http://localhost:8000/*`)
  - Évite les problèmes CORS
  - Le frontend utilise `API_BASE_URL = '/api'` par défaut
- **Option production / déploiement** : Appels directs si `NEXT_PUBLIC_API_URL` est défini
  - IMPORTANT : `NEXT_PUBLIC_API_URL` doit être la racine du backend, sans suffixe `/api`
  - Exemple OK : `NEXT_PUBLIC_API_URL=https://api.example.com`
  - Exemple KO : `NEXT_PUBLIC_API_URL=https://api.example.com/api`

### Robustesse (v1.1.33)
- **Backend** : supporte maintenant les routes *avec* et *sans* préfixe `/api`
  - `/activity/load` et `/api/activity/load` fonctionnent tous les deux
- **Observabilité** : chaque requête a un `X-Request-ID` et un fichier log est créé à chaque run (`./data/logs/backend_<timestamp>.log`)

### Variables d'environnement
```bash
# Optionnel - appels directs API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Par défaut (dev) : pas d'env => base "/api" (proxy Next)
```

## 📡 Endpoints API

```bash
# Upload et gestion
POST   /activity/load               # Upload GPX/FIT (multipart)
POST   /api/activity/load           # Upload GPX/FIT (multipart) - compatible
GET    /activities                  # Lister activités
GET    /api/activities              # Lister activités - compatible
DELETE /activity/{id}               # Supprimer activité
DELETE /api/activity/{id}           # Supprimer activité - compatible
DELETE /activities                  # Vider toutes
DELETE /api/activities              # Vider toutes - compatible

# Analyses  
GET    /activity/{id}/real            # Données course réalisée
GET    /activity/{id}/theoretical     # Prédictions temps/allure
GET    /activity/{id}/series/{name}   # Séries de données
GET    /activity/{id}/map             # Données cartographiques

# Toutes les routes ci-dessus existent aussi sous /api/* (compatibilité)

# Santé
GET    /health                      # Status backend + logs
GET    /api/health                  # Compatible
```

## 🏃 Fonctionnalités

## 📋 Vérification QA v1.1.42

### ✅ Fonctionnalités vérifiées
- **UI Layout**: Grille responsive 6 colonnes fonctionnelle
- **Sections collapsibles**: Pauses, Splits, Segments, Records, Efforts correctement implémentées
- **Réorganisation catégories**: Pauses sous Map, prédictions/charge sous Charts, efforts/records/segments sous Highlights
- **Map toggles**: Coloration par allure et points de pause fonctionnels
- **Graphiques**: Axe Y inversé pour allure, sélecteur temps/distance, tooltips corrects, graphique moving supprimé
- **Zones**: 3 sous-sections (HR/pace/puissance) avec tables Strava-like Z6→Z1
- **Power Duration Curve**: Graphique ligne W vs temps correct
- **Nouveaux graphiques**: 
  - "Temps intermédiaires" avec barres horizontales dans Pacing
  - "Allure par split" histogramme vertical dans Splits
- **Backend**: Calculs derive cardio vérifiés et cohérents

### ✅ Problèmes résolus (v1.1.42)
- **Tests backend**: Correction du test `test_compute_pace_vs_grade_data_basic` (ajout colonne `pace_n`)
- **Tests frontend**: Correction du test `HorizontalSplitsTable` (nombre de lignes correct)
- **Cohérence visuelle**: Correction des couleurs du graphe `VerticalPaceHistogram` (maintenant bleu comme les autres)
- **Stabilité**: Tous les tests passent (13/13 backend, 20/20 frontend)

### 🧪 Tests unitaires
- Tests complets pour tous les composants critiques (HorizontalSplitsTable, VerticalPaceHistogram, etc.)
- Couverture backend : 13/13 tests passent
- Couverture frontend : 20/20 tests passent  
- Version bumpée à v1.1.42 - STABLE

### Frontend Next.js (interface complète)
- **Upload rapide** : Dropzone react-dropzone avec gestion d'erreur réseau avancée
- **Métriques complètes** : 100+ métriques organisées par catégories (Summary, Power, Performance, Pacing, Garmin, Series, Map)
- **KPI header** : Distance, temps, dénivelé, allure moyenne avec affichage conditionnel
- **Tableaux intelligents** : Splits, best efforts, statistiques avec formatage automatique
- **Graphiques interactifs** : Recharts optimisés avec échantillonnage dynamique (>2500 points)
- **Métriques étendues** : FC, puissance, cadence, dynamique de course (FIT), zones Garmin
- **Registre centralisé** : Définitions unifiées des métriques avec rendu conditionnel GPX/FIT
- **Performance optimisée** : React.memo, useMemo, lazy loading, sampling intelligent
- **Responsive** : Mobile-friendly design avec adaptations automatiques

## 🧪 Tests

### Backend
```bash
# Compilation
python -m compileall backend

# Tests unitaires
python -m unittest discover -s tests -p "test_*.py" -v

# Tests ciblés (pytest)
python -m pytest tests/pytest/
```

### Frontend  
```bash
cd frontend
npm test          # Tests unitaires + intégration
npm run build     # Vérification TypeScript
```

### Smoke tests
```bash
# Validation rapide upload/parsing
python tests/smoke_test.py
```

## 🔧 Outils de développement

### Profilage performance
```bash
# Profilage GPX
python dev/scripts/profiling/profile_pipeline.py --input tests/course.gpx --mode all --repeat 3

# Profilage FIT  
python dev/scripts/profiling/profile_pipeline.py --input tests/course.fit --mode all --repeat 3
```

## 📋 Dépendances

### Python (requirements.txt)
```txt
# Runtime
gpxpy, fitparse, pandas, numpy, plotly

# API
fastapi, uvicorn[standard], python-multipart, pydantic, httpx

# Utilitaires
pytest, pyarrow
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "next": "16.1.5",
    "react": "19.2.3", 
    "react-dom": "19.2.3",
    "react-dropzone": "^14.3.8",
    "@tanstack/react-query": "^5.90.20",
    "lucide-react": "^0.563.0",
    "tailwindcss": "^4"
  }
}
```

## 🐛 Dépannage

### Erreur "Failed to proxy" / "ECONNREFUSED 127.0.0.1:8000"
- Le backend n'est pas demarre (ou pas encore pret). Lance l'app via `run_win.bat` / `run_linux.sh`.
- Verifie le health check: `curl http://127.0.0.1:8000/health`

### Problèmes d'upload
```bash
# Vérifier backend
curl http://127.0.0.1:8000/health

# Vérifier upload direct
curl -X POST http://127.0.0.1:8000/api/activity/load \
     -F "file=@test.gpx" -F "name=test"

# Logs frontend (console)
# Vérifier les erreurs réseau/CORS
```

### PowerShell: commandes manuelles

PowerShell ne supporte pas l'execution `"path" -m ...` sans l'operateur `&`.

```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### Ports par défaut
- Backend API : `8000` 
- Frontend Next.js : `3000` (ou `3001` si 3000 occupé)

## 📝 Notes développement

### Règles d'architecture
- `backend/core/` et `backend/services/` : pas d'import UI
- `frontend/` : **pas de dépendance backend directe** (API only)

### Ajout fonctionnalité
1. **Core** : Implémenter calcul dans `backend/core/`
2. **Services** : Orchestrer dans `backend/services/`  
3. **API** : Exposer via `backend/api/routes/`
4. **UI Frontend** : Composants React dans `frontend/src/`

---

## 📈 Changelog

Voir `CHANGELOG.md`.

## Garmin (auto-import)

Endpoints (v1.1.54+):
- `POST /integrations/garmin/connect`
- `POST /integrations/garmin/sync`
- `POST /integrations/garmin/reset`
- `GET /integrations/garmin/status`

Notes:
- Sur une premiere connexion, Garmin peut demander un code OTP (MFA). Le flux est gere dans l'UI Parametres.
- Filtre import: seules les activites Running / Trail Running sont importees.

Stockage:
- Activites: `data/activities/<uuid>/original.fit`, `df.parquet`, `meta.json`
- Tokens Garmin: `data/integrations/garmin/tokens/`

DB (PostgreSQL-ready):
- Par defaut: SQLite sous `data/coursescope.sqlite`
- Override: `COURSESCOPE_DATABASE_URL` (ex: `postgresql+psycopg://...`)

## Upload: persistance

Par defaut (v1.1.55+), l'upload n'enregistre pas l'activite sur disque (`persist_to_disk=false`).
- Avantage: test rapide sans polluer l'historique.
- Limite: l'activite reste accessible tant que le backend tourne.

Pour conserver l'historique sur disque, activer l'option dans `http://localhost:3000/settings`.

## Upload: type (reel vs theorique)

Depuis la page d'accueil:
- "Activite reelle": force l'analyse reelle.
- "Trace (theorique)": force l'analyse theorique.

Le type est envoye explicitement au backend via `activity_type` (plus d'auto-detection cote UI).
