# CourseScope (v1.1.20)

CourseScope est une application double-stack pour analyser des traces running GPX/FIT :
- **UI legacy Streamlit** : interface complète avec cartes, graphiques, et analyses avancées
- **Backend FastAPI** : API moderne pour les données d'activité avec registre de métriques centralisé
- **Frontend Next.js** : interface complète avec 100+ métriques, graphiques interactifs, et optimisations performance

## 🚀 Démarrage rapide

### Option 1 - Streamlit (recommandé pour usage complet)
```bash
# Windows
./run_win.bat

# Linux/macOS  
./run_linux.sh

# Manuel
python -m streamlit run CourseScope.py
```

### Option 2 - API + Frontend (développement)

**Backend API :**
```bash
cd "C:\Users\domin\Documents\Python Scripts\CourseScope"
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend Next.js :**
```bash
cd frontend
npm install
npm run dev    # développement
npm run build  # production
```

## 📁 Architecture du projet

```
CourseScope/
├── CourseScope.py                 # Entry point Streamlit legacy
├── run_win.bat / run_linux.sh     # Scripts de lancement rapide
├── requirements.txt               # Dépendances Python
├── backend/
│   ├── api/                     # API FastAPI
│   │   ├── main.py             # Serveur FastAPI + CORS + logs
│   │   └── routes/
│   │       ├── activities.py    # POST /activity/load (upload)
│   │       ├── analysis.py      # Analyses real/theoretical
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
│   └── ui/                      # Interface Streamlit
├── frontend/
│   ├── src/
│   │   ├── lib/api.ts          # Client API avec proxy
│   │   ├── components/upload/    # Upload dropzone
│   │   └── app/               # Pages Next.js
│   └── next.config.ts           # Configuration proxy API
└── tests/                       # Tests unitaires + intégration
```

## 🔌 Configuration API (v1.1.9)

### Stratégie de communication
- **Développement local** : Proxy Next.js (`/api/*` → `http://localhost:8000/*`)
  - Évite les problèmes CORS
  - URLs relatives dans le frontend (`/api/activity/load`)
- **Production** : Appels directs si `NEXT_PUBLIC_API_URL` défini

### Variables d'environnement
```bash
# Production - appels directs API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Développement - utilisation proxy (par défaut)
# NEXT_PUBLIC_API_URL non défini = mode proxy
```

## 📡 Endpoints API

```bash
# Upload et gestion
POST   /api/activity/load           # Upload GPX/FIT (multipart)
GET    /api/activities             # Lister activités
DELETE /api/activity/{id}          # Supprimer activité
DELETE /api/activities             # Vider toutes

# Analyses  
GET    /api/activity/{id}/real        # Données course réalisée
GET    /api/activity/{id}/theoretical # Prédictions temps/allure
GET    /api/activity/{id}/series/{name} # Séries de données
GET    /api/activity/{id}/map         # Données cartographiques

# Santé
GET    /api/health                  # Status backend + logs
```

## 🏃 Fonctionnalités

### Streamlit Legacy (usage complet)
- **Upload** : Glisser-déposer GPX/FIT
- **Cartographie** : Trace interactive avec Leaflet/pydeck
- **Graphiques** : Allure, altitude, fréquence cardiaque, puissance
- **Analyses avancées** : 
  - Splits automatiques (1000m, 1km, 5km)
  - Zones d'allure type Garmin
  - Grade Adjusted Pace (GAP)
  - Estimations temps théoriques
- **Métriques FIT** : Running dynamics, puissance normalisée (NP), TSS

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
python tools/profile_pipeline.py --input tests/course.gpx --mode all --repeat 3

# Profilage FIT  
python tools/profile_pipeline.py --input tests/course.fit --mode all --repeat 3
```

## 📋 Dépendances

### Python (requirements.txt)
```txt
# Streamlit
streamlit, gpxpy, fitparse, pandas, numpy, plotly, pydeck

# API FastAPI
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

### Problèmes d'upload
```bash
# Vérifier backend
curl http://localhost:8000/health

# Vérifier upload direct
curl -X POST http://localhost:8000/api/activity/load \
     -F "file=@test.gpx" -F "name=test"

# Logs frontend (console)
# Vérifier les erreurs réseau/CORS
```

### Ports par défaut
- Streamlit : `8501`
- Backend API : `8000` 
- Frontend Next.js : `3000` (ou `3001` si 3000 occupé)

## 📝 Notes développement

### Règles d'architecture
- `backend/core/` et `backend/services/` : **pas d'import Streamlit**
- `backend/ui/` : **uniquement Streamlit** 
- `frontend/` : **pas de dépendance backend directe** (API only)

### Ajout fonctionnalité
1. **Core** : Implémenter calcul dans `backend/core/`
2. **Services** : Orchestrer dans `backend/services/`  
3. **API** : Exposer via `backend/api/routes/`
4. **UI Streamlit** : Widgets dans `backend/ui/`
5. **UI Frontend** : Composants React dans `frontend/src/`

---

## 📈 Changelog

Voir `frontend/CHANGELOG.md` pour l'historique détaillé des versions.

**v1.1.20** (2025-01-30) - **Version majeure frontend**
- **Registre de métriques complet** : 100+ métriques avec formatage intelligent et affichage conditionnel GPX/FIT
- **Graphiques Recharts optimisés** : Échantillonnage dynamique, multi-axes, tooltips interactifs
- **Gestion d'erreur réseau avancée** : Messages utilisateur spécifiques, documentation de debug NETWORK_DEBUG.md
- **Optimisations performance** : React.memo, useMemo, lazy loading, cache intelligent
- **Tests étendus** : Couverture registre métriques, formatters, simulation erreurs réseau
- **Architecture modulaire** : Séparation formatting/logic, registry-driven rendering

**v1.1.9** : Nouveaux métriques backend + optimisations calcul + correction FIT datetime + tests/Docs a jour  
**v1.1.8** : Fix upload "Failed to fetch" + proxy Next.js + logs améliorés  
**v1.1.7** : UI metrics-only + métriques cardio  
**v1.1.6** : Backend consolidé + API endpoints  
**v1.1.5** : Transition FastAPI + Next.js initiée
