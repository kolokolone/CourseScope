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

- **Page** : `frontend/src/app/progress/page.tsx`
- **Données** : queries React Query ciblées (series, best-efforts, activities, HR/allure, waterfall, calendrier, charge et intensité)
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

Le rattachement d'une activité privilégie `local_date`, avec repli UTC uniquement pour les anciennes lignes. Le record reste calculé dans l'année affichée ; la série en cours traverse les changements d'année et reste active si la dernière séance date d'hier. La synthèse `jours actifs · record · série en cours` n'est affichée qu'une fois sous le titre.

### Performance
| Graphique | Composant | Statut |
|---|---|---|
| Best efforts progression | Inline dans `page.tsx` | ✅ |
| VO2max (3 derniers mois) | Inline dans `page.tsx` | ✅ |

L'axe VO2max commence à `95 %` de la plus petite valeur visible et conserve une marge supérieure, y compris lorsque toutes les valeurs sont identiques.

### Efficacité / Durabilité
| Graphique | Composant | Statut |
|---|---|---|
| Efficacité aérobie (EF) vs date | Inline dans `page.tsx` | ✅ |
| Découplage cardiaque | Inline dans `page.tsx` | ✅ |
| HR @ pace fixe (2-3 allures) | Inline dans `page.tsx` | ✅ |
| Pace @ HR fixe (2-3 FC) | Inline dans `page.tsx` | ✅ |

Les trois références HR@allure et allure@FC utilisent le même ordre de couleurs documentées dans les deux cartes : bleu théorique, teal allure et orange puissance. La moyenne lissée reste distincte en bleu marine pointillé.

### Phase 3 (qualité pro)
| Graphique | Composant | Statut |
|---|---|---|
| Pace-HR Waterfall 3D | `PaceHr3DChart.tsx` (react-three-fiber) | ✅ |
| Session taxonomy (tags) | Endpoint `/progress/session-taxonomy` | ✅ (endpoint) / ⚠️ (UI non implémentée) |
| Tags manuels | Endpoint `/progress/tags` | ✅ (endpoint) / ⚠️ (UI non implémentée) |

Les anciennes cartes « Répartition des séances », « Terrain » et « Sorties longues » ne sont plus rendues par `/progress` et ne déclenchent plus de requête. Les endpoints et tags restent disponibles pour compatibilité et pour les filtres réutilisés.

## Stratégie de calcul

- **Indexation asynchrone** : après upload/sync, l'indexation est lancée en thread background
- **Fast** : synchronisation FS ↔ DB (sans recalcul lourd)
- **Slow** : recalcul des métriques analytiques (incrémentale ou complète)
- **Statut** : polling `GET /progress/index/status` côté frontend
- **Déclenchement** : automatique à l'ouverture de `/progress` + manuel dans `/settings`

### Zones de fréquence cardiaque

Les zones Z1 à Z5 utilisent respectivement `50–60 %`, `60–70 %`, `70–80 %`, `80–90 %` et `≥ 90 %` de la FC max effective. Une indexation lente résout un snapshot unique de FC max (`manual` ou `detected`) avant de calculer toutes les activités ; `progress_activity_index` conserve la valeur et sa provenance. Modifier la valeur manuelle ou sa source lance un recalcul complet. Tant que les lignes ne correspondent pas à la FC max courante, l'API marque les zones obsolètes et ne renvoie pas les anciens temps comme s'ils étaient actuels.

### Prétraitement Pace-HR

Le Waterfall et les séries HR@Pace/Pace@HR utilisent des bins pré-calculés après un nettoyage volontairement simple : allure continue sur 30 secondes, filtre Hampel FC sur 11 secondes, médiane FC sur 5 secondes et exclusion des 10 premières minutes avec distance positive. Le pipeline n'applique ni masque de mouvement, ni segmentation des trous, ni contrôle de saut FC, ni exclusion des transitions d'allure.

Les index natifs `5/10/20/30 s/km` sont calculés séparément lors de l'indexation. L'API Waterfall sélectionne l'index demandé sans refaire de calcul statistique. Le détail est documenté dans [pace_hr_waterfall.md](pace_hr_waterfall.md).

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
