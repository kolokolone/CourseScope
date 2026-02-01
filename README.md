# CourseScope (v1.1.5)

CourseScope est une app Streamlit locale pour analyser des traces running GPX/FIT (carte, graphes, splits, zones type Garmin, GAP/pente) et estimer un temps theorique sur un trace selon une allure de base et la pente. Backend Python prepare pour une future API.

La v1.1 est une refacto interne (aucune feature supprimee) qui separe:
- `core/` (pur Python)
- `services/` (orchestration, pur Python)
- `ui/` (Streamlit, rendu uniquement)

Version courante: v1.1.5 (patch de v1.1)

Depuis v1.1.1, le backend est durci pour preparer une migration FastAPI/React:
- contrat DataFrame canonique (validation/coercion)
- cache portable injectable
- serialisation JSON
- batterie de tests unitaires

Depuis v1.1.2, la racine du projet est simplifiee:
- suppression du shim `grade_table.py` (utiliser `core/grade_table.py`)
- table "Ref pro" embarquee dans `core/resources/pro_pace_vs_grade.csv` (surcharge possible via `COURSESCOPE_PRO_PACE_VS_GRADE_PATH`)


## Prerequis

- Python 3.11+ (recommande)
- Acces internet au premier lancement (installation pip)

Dependances principales (voir `requirements.txt`):
- streamlit
- gpxpy
- fitparse
- pandas, numpy
- plotly
- pydeck


## Lancer l'application

### Windows (recommande)

Depuis le dossier du projet:

1) Double-clique: `run_win.bat`

Ce script:
- cree/active `.venv`
- installe `requirements.txt`
- lance Streamlit sur `CourseScope.py`

### Linux/macOS

Depuis le dossier du projet:

```bash
./run_linux.sh
```

### Manuel

Creer un venv puis installer les dependances.

Creer le venv:

```bash
python -m venv .venv
```

Activer le venv:

Windows (cmd):

```bat
.venv\Scripts\activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Installer et lancer:

```bash
pip install -r requirements.txt
streamlit run CourseScope.py
```


## Utilisation

1) Ouvrir l'app dans le navigateur (URL affichee par Streamlit).
2) Uploader un fichier `.gpx` ou `.fit`.
3) Choisir la vue:
   - "Donnees de la course realisee"
   - "Donnees theoriques (prevision)"

Notes:
- L'historique est stocke en session (sidebar) et permet de recharger rapidement un fichier.
- Les allures sont affichees en min/km.


## Metriques FIT (optionnelles)

Quand le fichier `.fit` contient les champs, l'app calcule/affiche des metriques supplementaires (style Garmin), par ex:
- Running dynamics: `stride_length_m`, `vertical_oscillation_cm`, `vertical_ratio_pct`, `ground_contact_time_ms`, `gct_balance_pct`
- Puissance avancee (si power dispo): `normalized_power_w` (NP), `intensity_factor`, `tss`

Compatibilite:
- GPX reste supporte: ces colonnes existent dans le DataFrame canonique mais restent `NaN`.
- Si une metrique FIT est absente: valeur `NaN`/`None` et l'UI masque les panneaux associes.


## Profilage (perf)

Un harness de profilage (sans Streamlit) est fourni pour mesurer rapidement le backend sur un fichier GPX/FIT.

Depuis la racine du projet (Windows, venv actif):

```bat
.venv\Scripts\python.exe tools\profile_pipeline.py --input tests\course.gpx --mode all --repeat 3 --json-out profiles\profile_gpx.json
.venv\Scripts\python.exe tools\profile_pipeline.py --input tests\course.fit --mode all --repeat 3 --json-out profiles\profile_fit.json
```

Notes:
- `profiles/` est un dossier local (ignore par git).
- `--tracemalloc` existe mais ajoute un surcout important (a reserver a des diagnostics memoire).


## Tests

La v1.1.4 fournit:
- des smoke tests minimalistes (sans framework) pour eviter les regressions
- des tests unitaires (unittest) pour valider les fonctions de base apres refacto

### Smoke tests

Sous Windows (avec le venv cree par `run_win.bat`):

```bat
.venv\Scripts\python.exe tests\smoke_test.py
```

Sous Linux/macOS:

```bash
.venv/bin/python tests/smoke_test.py
```

Ces tests utilisent les fichiers demo:
- `tests/course.gpx`
- `tests/course.fit`

### Tests unitaires

Depuis le dossier du projet (avec le venv actif):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Tests pytest

La suite pytest (tests cibles) vit dans `tests/pytest/`.

```bash
python -m pytest -q
```

### Compilation (sanity check)

```bash
python -m compileall -q core services ui tests CourseScope.py
```


## Structure du projet (v1.1.4)

```
  CourseScope/
  CourseScope.py
  run_win.bat
  run_linux.sh
  requirements.txt
  core/
  services/
  ui/
  tests/
  tools/
```

### Core (pur Python)
- `core/gpx_loader.py`, `core/fit_loader.py`: parsing -> DataFrame canonique
- `core/contracts/activity_df_contract.py`: contrat/validation DF canonique
- `core/constants.py`: constantes partagees (seuils, defaults)
- `core/stats/basic_stats.py`: stats de base unifiees
- `core/derived.py`: bundle de series derivees
- `core/real_run_analysis.py`: calculs + figures Plotly (reel)
- `core/ref_data.py`: providers de donnees de reference (ex: Ref pro)
- `core/transform_report.py`: reporting testable (rows_in/rows_out)
- `core/metrics.py`: stats style Garmin + zones
- `core/theoretical_model.py`: modele theorique + figures Plotly
- `core/formatting.py`, `core/parsing.py`: helpers partages
- `core/grade_table.py`: correction d'allure selon la pente (canonical)
- `core/resources/pro_pace_vs_grade.csv`: table de reference "Ref pro" (optionnelle)

Pour utiliser une table personnalisable par l'utilisateur:
- definir `COURSESCOPE_PRO_PACE_VS_GRADE_PATH` vers un fichier CSV (meme schema)

### Services (backend applicatif, pur Python)
- `services/activity_service.py`: chargement + type detection + stats sidebar
- `services/real_activity_service.py`: orchestration analyse reel
- `services/theoretical_service.py`: orchestration prevision
- `services/history_service.py`: helpers d'historique (pure functions)
- `services/models.py`: dataclasses (contrats)
- `services/cache.py`: cache portable (preparation migration API)
- `services/serialization.py`: conversion en structures JSON-serialisables
- `services/analysis_service.py`: points d'entree backend de haut niveau (cache injectable)

### UI (Streamlit)
- `ui/layout.py`: navigation + uploader + historique
- `ui/real_run_view.py`: widgets + rendu reel
- `ui/theoretical_view.py`: widgets + rendu theorique


## Notes pour developpement / contributions

Regle principale v1.1.4:
- `core/` et `services/` ne doivent pas importer Streamlit.
- Streamlit reste confine a `ui/`.

Regle v1.1.4 (prepa API):
- valider le DataFrame canonique a la frontiere service (voir services/activity_service.py)
- pour une future API, utiliser services/analysis_service.py + services/serialization.py

Si tu ajoutes une nouvelle fonctionnalite:
1) Implementer le calcul dans `core/`.
2) Orchestrer dans `services/` (structures de retour stables).
3) Ajouter les widgets/rendu dans `ui/`.
4) Ajouter/etendre `tests/smoke_test.py` si pertinent.


## Changelog

Voir `change_log.txt`.
