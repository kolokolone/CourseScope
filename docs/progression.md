# Progression (tendances multi-activités)

> **Type** : Spécification · **Page** : `/progress` · **Endpoints** : `/progress/*`
> **Statut** : ✅ Phases 1, 2, 3 implémentées

## Objectif

Page de dashboard permettant de visualiser l'évolution des performances et de la charge d'entraînement au fil du temps, par comparaison de toutes les activités enregistrées.

## Architecture implémentée

### Backend

- **Base de données** : SQLite (`data/coursescope.sqlite`), tables préfixées `progress_*`
- **Index analytique** : `progress_activity_index` (1 ligne par activité) + tables dérivées
- **Indexation** : Système fast/slow (cf. `docs/indexation.md`)
- **Endpoints** : 15 endpoints sous `/progress/*` (indexation, activities, series, best-efforts, hr-at-pace, pace-at-hr, session-taxonomy, tags, pace-hr-waterfall, training-load, calendar)

Détails : voir `docs/metrics_catalog.md` (section Progression API).

### Frontend

- **Page** : `frontend/src/app/progress/page.tsx` (1206 lignes)
- **Données** : 8 queries React Query parallèles (series, best-efforts, activities, hr-at-pace, pace-at-hr, waterfall, calendar, training-load)
- **Hooks** : `frontend/src/hooks/useProgress.ts`
- **API client** : `frontend/src/lib/api.ts` (module `progressApi`)

## Graphiques implémentés

### Volume / Charge
| Graphique | Composant | Statut |
|---|---|---|
| Volume hebdo (km, temps, D+) | Inline dans `page.tsx` | ✅ |
| TRIMP par semaine + ACWR | `TrainingLoadChart.tsx` | ✅ |
| Calendrier (heatmap) | `CalendarHeatmap.tsx` | ✅ |

Le calendrier annuel étire ses colonnes de semaines sur la largeur disponible. Les libellés des jours, les mois et les cellules utilisent une seule grille CSS à 7 lignes : leur alignement ne dépend donc plus d'une hauteur fixe ou d'un décalage manuel. Chaque cellule expose au survol ou au focus clavier une infobulle opaque, basée sur le token `--card`, avec la date, la distance, la durée et le nombre d'activités.

### Performance
| Graphique | Composant | Statut |
|---|---|---|
| Best efforts progression | Inline dans `page.tsx` | ✅ |
| VO2max (3 derniers mois) | Inline dans `page.tsx` | ✅ |

### Efficacité / Durabilité
| Graphique | Composant | Statut |
|---|---|---|
| Efficacité aérobie (EF) vs date | Inline dans `page.tsx` | ✅ |
| Découplage cardiaque | Inline dans `page.tsx` | ✅ |
| HR @ pace fixe (2-3 allures) | Inline dans `page.tsx` | ✅ |
| Pace @ HR fixe (2-3 FC) | Inline dans `page.tsx` | ✅ |

### Phase 3 (qualité pro)
| Graphique | Composant | Statut |
|---|---|---|
| Pace-HR Waterfall 3D | `PaceHr3DChart.tsx` (react-three-fiber) | ✅ |
| Session taxonomy (tags) | Endpoint `/progress/session-taxonomy` | ✅ (endpoint) / ⚠️ (UI non implémentée) |
| Tags manuels | Endpoint `/progress/tags` | ✅ (endpoint) / ⚠️ (UI non implémentée) |

## Stratégie de calcul

- **Indexation asynchrone** : après upload/sync, l'indexation est lancée en thread background
- **Fast** : synchronisation FS ↔ DB (sans recalcul lourd)
- **Slow** : recalcul des métriques analytiques (incrémentale ou complète)
- **Statut** : polling `GET /progress/index/status` côté frontend
- **Déclenchement** : automatique à l'ouverture de `/progress` + manuel dans `/settings`

## Performance

- Latence cible : < 200 ms pour les requêtes de séries
- Pas de scan filesystem par requête (tout passe par SQLite)
- Pas de chargement de `df.parquet` pour les dashboards
- Données renvoyées en buckets (week/month), downsampling côté backend

## Tests

- **Backend** : `tests/pytest/test_progress_indexation_runner.py`, `tests/pytest/test_progress_endpoints.py`
- **Frontend** : `frontend/src/app/progress/page.test.tsx` (smoke test)
- **Endpoints** : fast add/remove, slow stale detection, idempotence, concurrence

## Références

- Intensité / distribution : https://pubmed.ncbi.nlm.nih.gov/20861519/
- Critical power/speed : https://pmc.ncbi.nlm.nih.gov/articles/PMC5371646/
- Running economy : https://pmc.ncbi.nlm.nih.gov/articles/PMC4555089/
- Cardiovascular drift : https://journals.lww.com/acsm-essr/fulltext/2001/04000/
- Session-RPE load : https://journals.lww.com/nsca-jscr/abstract/2001/02000/
- TRIMP / fitness-fatigue : https://pubmed.ncbi.nlm.nih.gov/6778623/
- ACWR framing : https://pmc.ncbi.nlm.nih.gov/articles/PMC4789704/
