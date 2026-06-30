# Modifications à implémenter — CourseScope

Date : 2026-07-01 01:00
Source : agents/modifications.txt
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

L'utilisateur a formulé 4 demandes dans `agents/modifications.txt` :

1. **Audit frontend** des recalculs redondants lors de la navigation entre pages, avec propositions d'amélioration.
2. **Analyse du log spam backend** — l'endpoint `/progress/index/status` est appelé toutes les ~2 secondes même quand l'indexation est terminée.
3. **Correction/amélioration des monolithes backend** — bien que le CHANGELOG v1.1.95 affirme des refactors, plusieurs fichiers ont regrossi ou restent problématiques.
4. **Version unique centralisée** — remplacer les 4+ occurrences hardcodées de `"1.2.0"` par une source unique.

**Logique de priorisation** : Les demandes 2 et 4 sont P0 (corrections à fort impact / faible risque). La demande 3 est P1 (dette technique à résorber progressivement). La demande 1 est P1 (amélioration de performance et UX, mais non bloquante).

**Résultat attendu** : 4 lots de modifications indépendants livrables séparément, chacun avec tests et vérifications.

---

## 2. Demandes utilisateur extraites

### Demande 1 — Audit recalculs frontend

- **Texte source** : « lancer un audit du frontend pour voir ce qui est calculé à chaque fois qu'on se rend sur une page puis recalculé si on revient sur la meme page, cibler ce qui peut etre amélioré pour éviter ces recalculs redondants puis comment l'améliorer »
- **Interprétation** : L'utilisateur constate que les données sont refetchées inutilement lorsqu'il navigue entre pages ou revient sur une page déjà visitée. Il veut un diagnostic précis et des actions correctives.
- **Statut** : retenue
- **Justification** : Problème réel confirmé par l'audit. Le QueryClient n'a pas de `staleTime` global (défaut 0), donc toutes les queries sont immédiatement périmées. Combiné à `refetchOnMount: true` (défaut), chaque navigation déclenche un refetch.

### Demande 2 — Log spam `/progress/index/status`

- **Texte source** : « analyser pourquoi j'ai ceci dans le log backend : "INFO: 127.0.0.1:56299 - GET /progress/index/status HTTP/1.1 200 OK" [toutes les ~2 secondes] »
- **Interprétation** : L'utilisateur voit un déluge de logs pour un endpoint de statut d'indexation. Il veut comprendre pourquoi et corriger.
- **Statut** : retenue
- **Justification** : Deux causes identifiées : (a) le `request_logging_middleware` dans `main.py` log TOUTES les requêtes en INFO, y compris les requêtes de polling ; (b) le `useEffect` de la page Progress démarre un `setInterval` à 2s qui ne s'arrête que si `state.running === false`, mais même après arrêt, le middleware loggue chaque appel.

### Demande 3 — Monolithes backend

- **Texte source** : « corriger/améliorer les monolithes backend »
- **Interprétation** : L'utilisateur sait que des refactors ont été faits (CHANGELOG v1.1.95) mais constate que le problème persiste ou est revenu. Il veut une action ciblée sur les vrais problèmes restants.
- **Statut** : retenue, scope limité
- **Justification** : 3 cibles prioritaires identifiées : (a) 16× duplication du pattern `db_session_factory` dans `routes/progress.py` ; (b) `core/metrics.py` (788 lignes, fonction god de 415 lignes) ; (c) `progress/indexation_runner.py` (777 lignes) et `progress/indexer.py` (734 lignes).

### Demande 4 — Version unique centralisée

- **Texte source** : « Comment gérer le numero de version de manière globale avec qu'un seul fichier ? comment font les vrais développeurs pour changer qu'une valeur qui se répercute partout ? je veux faire pareil »
- **Interprétation** : L'utilisateur veut un fichier unique (ex: `VERSION` à la racine) dont la valeur est lue par le backend Python, le frontend Next.js, et idéalement le Dockerfile.
- **Statut** : retenue
- **Justification** : 4 fichiers contiennent `"1.2.0"` en dur : `backend/api/main.py` (×2), `frontend/package.json`, `CHANGELOG.md`. Pattern standard : fichier `VERSION` à la racine + scripts de synchronisation.

---

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `agents/modifications.txt`
- `AGENTS.md`
- `README.md`
- `CHANGELOG.md`
- `docs/style-frontend-ui.md`
- `backend/api/main.py`
- `backend/api/routes/progress.py` (677 lignes)
- `backend/progress/indexation_runner.py` (777 lignes)
- `backend/progress/indexer.py` (734 lignes)
- `backend/core/metrics.py` (788 lignes — partiellement)
- `frontend/src/app/layout.tsx`
- `frontend/src/app/providers.tsx`
- `frontend/src/app/progress/page.tsx` (489 lignes)
- `frontend/src/hooks/useProgress.ts` (237 lignes)
- `frontend/src/hooks/useActivity.ts` (256 lignes)
- `frontend/src/lib/api.ts` (partiellement)
- `frontend/package.json`

### 3.2 Constats établis

- **Fait 1** : Le `QueryClient` dans `providers.tsx` ne définit PAS `staleTime` → défaut 0ms → toute query est immédiatement stale après son premier fetch.
- **Fait 2** : `refetchOnMount` n'est pas désactivé → défaut `true` → chaque montage de composant avec une query stale déclenche un refetch.
- **Fait 3** : Le `request_logging_middleware` dans `main.py` (lignes 99-137) loggue TOUTES les requêtes en niveau INFO, sans filtrage par path ou fréquence.
- **Fait 4** : La page Progress (`page.tsx` lignes 61-144) contient un `useEffect` qui démarre un `setInterval` à 2000ms pour poller `/progress/index/status`, et ne l'arrête que si `state.running === false`. La condition d'arrêt suppose que `running` passe à `false`, ce qui n'arrive que si l'indexation se termine normalement.
- **Fait 5** : Même quand l'indexation est terminée, le composant `MaintenanceSettings` dans Settings utilise `refetchInterval` qui continue de poller toutes les 5s (ou 2s si running).
- **Fait 6** : `backend/api/routes/progress.py` (677 lignes) contient 16 répétitions du pattern `db_session_factory = getattr(request.app.state, "db_session_factory", None); if db_session_factory is None: raise HTTPException(...)`. `traces.py` a déjà un helper `_get_db_session_factory` pour ce pattern.
- **Fait 7** : `backend/core/metrics.py` (788 lignes) contient `compute_garmin_like_stats` (415 lignes, 293 appels, 41 `if`) — la plus grosse fonction du backend.
- **Fait 8** : `backend/progress/indexer.py` (734 lignes) contient `index_activity` (379 lignes).
- **Fait 9** : La version `"1.2.0"` est hardcodée dans `backend/api/main.py` lignes 93 et 191, `frontend/package.json` ligne 3, `CHANGELOG.md` ligne 7.
- **Fait 10** : Aucun fichier `VERSION`, `pyproject.toml`, `setup.cfg` ou `__version__` n'existe côté backend.
- **Fait 11** : Toutes les queries individuelles dans les hooks (`useActivity.ts`, `useProgress.ts`, etc.) ont leur propre `staleTime` explicite (1min, 5min, 10min selon le type) — ce qui mitige partiellement le problème du `staleTime: 0` global.

### 3.3 Hypothèses

- **Hypothèse 1** : Le log spam est acceptable en environnement de développement mais gênant en production. Le middleware de logging est trop verbeux pour les endpoints de polling.
- **Hypothèse 2** : Le `setInterval` de la page Progress ne s'arrête pas correctement si l'indexation échoue silencieusement ou si `state.running` reste bloqué. Le timeout de 20s en fallback est une rustine.
- **Hypothèse 3** : Les monolithes listés (metrics.py, indexer.py, indexation_runner.py) n'ont pas été touchés lors du refactor v1.1.95 car ils étaient déjà "assez propres" — mais ce n'est plus le cas.

### 3.4 Incertitudes

- **Incertitude 1** : Le `ProgressIndexationBanner` sur la page Settings (`MaintenanceSettings.tsx`) utilise `refetchInterval` sur une query `['progress', 'index-status']` avec un `staleTime` de 2s. Ce composant est-il toujours affiché quand l'utilisateur quitte la page ? Si oui, le polling continue en arrière-plan même sur d'autres pages → à vérifier (le composant est unmounté si on quitte `/settings`).
- **Incertitude 2** : Le découpage de `compute_garmin_like_stats` (415 lignes) en sous-fonctions pourrait casser des dépendances implicites. Une analyse plus fine des appels internes est nécessaire avant split.
- **Incertitude 3** : La version dans `CHANGELOG.md` doit-elle être automatisée ou rester manuelle ? Si automatisée, quel format (lien vers le fichier VERSION ? script de release ?).

---

## 4. Spécification fonctionnelle cible

### Lot 1 — Optimisation du cache React Query (Demande 1)

**Comportement attendu** :
- Naviguer vers une page déjà visitée dans les N dernières minutes ne déclenche PAS de refetch — les données en cache sont utilisées.
- Les données de progression (volume, TRIMP, best efforts, HR@pace, etc.) restent fraîches 5 minutes après leur premier chargement.
- Les données d'activité (analyse réelle, carte, séries) restent fraîches 10 minutes.
- La liste d'activités reste fraîche 2 minutes (au lieu d'1 minute actuellement — compromis performance/fraîcheur).
- Les requêtes dont les données n'ont pas changé (ex: version, configuration) ne sont pas refetchées à chaque navigation.

**États à gérer** :
- **Loading** : inchangé (les skeletons existants restent valides).
- **Fresh data** : affichée depuis le cache sans refetch réseau.
- **Stale data** : affichée depuis le cache + refetch silencieux en arrière-plan (comportement React Query par défaut avec `staleTime` configuré).

**Règles** :
- Le `staleTime` global doit être configuré à une valeur raisonnable (30s recommandé) pour servir de filet de sécurité aux queries sans `staleTime` explicite.
- Les `staleTime` existants par query (1min, 5min, 10min) restent inchangés ou sont légèrement augmentés.
- `gcTime` (garbage collection) doit être configuré à au moins 30 minutes pour éviter de perdre le cache lors de navigations rapides.

### Lot 2 — Correction du log spam (Demande 2)

**Comportement attendu** :
- Les logs backend ne montrent PLUS de lignes `GET /progress/index/status` toutes les 2 secondes quand l'utilisateur n'est PAS sur la page Progression ou Settings.
- Quand l'indexation est terminée, le polling s'arrête définitivement et ne redémarre pas.
- Les logs de requêtes de polling (status, health) sont en niveau DEBUG, pas INFO — ou filtrés par le middleware.

**Parcours utilisateur** :
1. L'utilisateur ouvre `/progress` → l'indexation est déjà faite → **aucun polling n'est lancé** (correction : actuellement le polling démarre même si `running=false` car le fallback timeout de 20s est toujours activé en cas d'erreur).
2. L'utilisateur ouvre `/progress` → l'indexation est en cours → le polling démarre à 2s → l'indexation se termine → le polling s'arrête → **les logs redeviennent silencieux**.
3. L'utilisateur quitte `/progress` → le polling est **immédiatement** nettoyé (clearInterval dans le cleanup de l'useEffect).

### Lot 3 — Réduction ciblée des monolithes (Demande 3)

**Comportement attendu** :
- `backend/api/routes/progress.py` : le pattern `db_session_factory` est extrait dans un helper partagé → réduction de ~50 lignes de duplication.
- `backend/core/metrics.py` : `compute_garmin_like_stats` (415 lignes) est découpée en sous-fonctions privées dans le même module (split horizontal, pas de nouveau fichier pour limiter le risque).
- `backend/progress/indexer.py` : `index_activity` (379 lignes) est découpée en sous-fonctions privées.
- Aucun endpoint, schéma ou contrat API n'est modifié.

### Lot 4 — Version unique centralisée (Demande 4)

**Comportement attendu** :
- Un fichier unique `VERSION` à la racine du repo contient `1.2.0`.
- `backend/api/main.py` lit ce fichier pour `FastAPI(version=...)` et `@app.get("/")`.
- `frontend/package.json` peut être synchronisé via un script `npm run sync-version` (ou lu dynamiquement).
- Le Dockerfile utilise `--build-arg VERSION` pour injecter la version.
- `CHANGELOG.md` référence la version de manière manuelle (pas d'automatisation forcée).

**Valeur utilisateur** : Une seule ligne à changer pour bump la version partout. Cohérent avec les pratiques standard de l'industrie (fichier `VERSION`, `version.txt`, `pyproject.toml`, etc.).

---

## 5. Spécification technique proposée

### 5.1 Frontend

#### Lot 1 — Optimisation React Query

**Fichier à modifier** : `frontend/src/app/providers.tsx`

**Modification** : Ajouter `staleTime` et `gcTime` globaux dans `defaultOptions.queries` :

```tsx
new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30 * 1000,        // 30 secondes par défaut
      gcTime: 30 * 60 * 1000,      // 30 minutes de garbage collection
    },
  },
})
```

**Fichiers à vérifier (pas de modification nécessaire, juste vérification)** :
- `frontend/src/hooks/useActivity.ts` — les `staleTime` explicites (1min, 2min, 5min, 10min) écrasent déjà le défaut global → OK.
- `frontend/src/hooks/useProgress.ts` — idem avec 1min → OK.
- `frontend/src/hooks/useGoals.ts` — à vérifier que le staleTime est bien défini.
- `frontend/src/hooks/useTraces.ts` — à vérifier.
- `frontend/src/hooks/useSettings.ts` — à vérifier.

**Hooks à ajuster si staleTime absent** :
- Vérifier chaque hook et ajouter `staleTime` là où il manque (le défaut global de 30s couvre les oublis, mais explicite est mieux).

**Contraintes UI** : Aucun changement visuel. Respecte `docs/style-frontend-ui.md`.

#### Lot 2 — Correction polling

**Fichier à modifier** : `frontend/src/app/progress/page.tsx`

**Modifications** :

1. **Ligne 74** : Remplacer l'invalidation large `['progress']` par des invalidations ciblées :
```tsx
// AVANT (trop large)
void queryClient.invalidateQueries({ queryKey: ['progress'] });

// APRÈS (ciblé)
void queryClient.invalidateQueries({ queryKey: progressKeys.series() });
void queryClient.invalidateQueries({ queryKey: progressKeys.bestEfforts() });
void queryClient.invalidateQueries({ queryKey: progressKeys.activities() });
// etc. pour chaque sous-groupe nécessaire
```

2. **Lignes 84-136** : Réécrire la logique de polling pour :
   - Ne PAS démarrer le polling si l'indexation n'est pas `running` après l'appel initial.
   - Supprimer le fallback timeout de 20s (lignes 129-134) qui force 20s de polling même sans indexation.
   - S'assurer que le `clearInterval` est appelé dans le `return` de cleanup du `useEffect`.

3. **Alternative recommandée** : Remplacer le `setInterval` manuel par une query React Query avec `refetchInterval` conditionnel (comme le fait déjà `MaintenanceSettings.tsx`). Cela unifie le pattern et bénéficie du cache React Query.

```tsx
// Pattern recommandé (cohérent avec MaintenanceSettings)
const indexStatusQuery = useQuery({
  queryKey: ['progress', 'index-status'],
  queryFn: () => progressApi.indexStatus(),
  staleTime: 2_000,
  refetchInterval: (query) => {
    const state = query.state.data;
    return state?.running ? 2_000 : false; // false = stop polling
  },
});
```

**Fichier à vérifier** : `frontend/src/components/features/settings/MaintenanceSettings.tsx` — confirmer que son `refetchInterval` ne pollue pas les logs quand l'utilisateur n'est pas sur `/settings`.

### 5.2 Backend

#### Lot 2 — Log spam (côté backend)

**Fichier à modifier** : `backend/api/main.py`

**Modification** : Ajouter un filtre dans `request_logging_middleware` pour logger les endpoints de polling/health en DEBUG au lieu de INFO :

```python
# Lignes 127-136, remplacer par :
_polling_paths = {"/progress/index/status", "/health"}
if request.url.path.rstrip("/") in _polling_paths:
    logger.debug("request", extra={...})  # DEBUG au lieu de INFO
else:
    logger.info("request", extra={...})
```

Alternative plus propre : créer un set configurable de paths à logger en `DEBUG` (`COURSESCOPE_LOG_QUIET_PATHS`).

#### Lot 3 — Monolithes

**Fichier à créer** : `backend/api/_helpers.py` (ou utiliser l'existant s'il est déjà créé)

**Contenu** : Extraire le helper `get_db_session_factory` (déjà présent dans `traces.py` en local) :

```python
from fastapi import HTTPException, Request

def get_db_session_factory(request: Request):
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")
    return factory
```

**Fichiers à modifier** :
1. `backend/api/routes/progress.py` : remplacer les 16 occurrences du pattern par `from api._helpers import get_db_session_factory` + appel `db_session_factory = get_db_session_factory(request)`. Gain : ~48 lignes supprimées.
2. `backend/api/routes/settings.py` : remplacer 3 occurrences.
3. `backend/api/routes/garmin_integration.py` : remplacer 3 occurrences.
4. `backend/api/routes/activities.py` : remplacer 1 occurrence.
5. `backend/api/routes/traces.py` : remplacer le helper local `_get_db_session_factory` par l'import partagé.

**Fichier à modifier** : `backend/core/metrics.py`

**Modification** : Découper `compute_garmin_like_stats` en sous-fonctions privées :
- `_compute_hr_zones(df, hr_max, hr_rest)` → stats FC (zones, moyenne, max)
- `_compute_pace_zones(df, pace_zones)` → stats allure
- `_compute_power_zones(df, ftp)` → stats puissance (si données)
- `_compute_cadence_stats(df)` → stats cadence
- `_compute_running_dynamics(df)` → dynamique de course
- `_compute_training_load_metrics(df, hr_max, hr_rest)` → TRIMP, charge
- `compute_garmin_like_stats(...)` → orchestre les appels ci-dessus (~30 lignes)

**Contrainte** : Toutes les sous-fonctions restent dans `metrics.py` (pas de nouveaux fichiers pour cette itération). Le contrat de la fonction publique `compute_garmin_like_stats` reste inchangé. Le dictionnaire retourné doit être strictement identique.

**Fichier à modifier** : `backend/progress/indexer.py`

**Modification** : Découper `index_activity` en sous-fonctions privées :
- `_classify_and_tag(session, df, meta, activity_id)` → classification + tags auto
- `_compute_progress_bins(session, df, activity_id, hr_max)` → bins HR/pace
- `_persist_progress_index(session, index_row, zones, splits, climbs, ...)` → écriture DB
- `index_activity(...)` → orchestrateur (~30 lignes)

#### Lot 4 — Version centralisée

**Fichier à créer** : `VERSION` (racine du repo)

**Contenu** :
```
1.2.0
```

**Fichier à modifier** : `backend/api/main.py`

**Modification** (lignes 6-7 et 91-96 et 188-194) :

```python
# En haut du fichier, ajouter :
from pathlib import Path

def _read_version() -> str:
    """Lit la version depuis le fichier VERSION à la racine du repo."""
    version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"  # fallback

_APP_VERSION = _read_version()

# Ligne 94 : remplacer version="1.2.0" par version=_APP_VERSION
app = FastAPI(
    title="CourseScope API",
    description="Analytics pour traces GPX/FIT",
    version=_APP_VERSION,
    lifespan=lifespan,
)

# Ligne 191 : remplacer "version": "1.2.0" par "version": _APP_VERSION
```

**Fichier à vérifier** : `frontend/package.json`

**Approche recommandée** : Ajouter un script npm `sync-version` qui lit `VERSION` et met à jour `package.json`. Exécuter ce script dans `run_win.bat` / `run_linux.sh` au démarrage.

```json
// package.json
"scripts": {
  "sync-version": "node -e \"const v=require('fs').readFileSync('../VERSION','utf8').trim();const p=require('./package.json');p.version=v;require('fs').writeFileSync('./package.json',JSON.stringify(p,null,2)+'\\n')\""
}
```

**Fichier à vérifier** : `Dockerfile` — ajouter `ARG VERSION` et le passer au build si pertinent.

**Fichier NON modifié** : `CHANGELOG.md` — reste manuel (les entrées de changelog sont rédigées par un humain).

### 5.3 Données et métriques

Aucun changement de métrique, schéma ou endpoint dans ces 4 lots. Tous les changements sont structurels (refactor, config, logging).

### 5.4 Documentation

- **`docs/metrics_catalog.md`** : Pas de mise à jour nécessaire (aucun endpoint modifié).
- **`README.md`** : Pas de mise à jour nécessaire (pas de nouvelle fonctionnalité).
- **`docs/style-frontend-ui.md`** : Pas de mise à jour nécessaire.
- **`CHANGELOG.md`** : À mettre à jour manuellement après implémentation (nouvelle entrée `1.2.1` ou `1.3.0`).
- **`docs/documentation_update_runbook.md`** : Pas de mise à jour nécessaire.

---

## 6. Plan d'implémentation pour agent-dev

### Étape 1 — Version unique centralisée (Lot 4, P0)

**Objectif** : Créer le fichier `VERSION` et faire lire la version par le backend.

**Fichiers** :
- `VERSION` (créer)
- `backend/api/main.py` (modifier, ~10 lignes changées)

**Détails d'implémentation** :
1. Créer `VERSION` à la racine avec `1.2.0`.
2. Dans `main.py`, ajouter `_read_version()` qui lit `VERSION`.
3. Remplacer les 2 occurrences hardcodées par `_APP_VERSION`.
4. Ajouter le script `sync-version` dans `frontend/package.json`.

**Tests à prévoir** :
- `python -c "from backend.api.main import _APP_VERSION; print(_APP_VERSION)"` → doit afficher `1.2.0`.
- `curl http://localhost:8000/ | grep version` → doit contenir `1.2.0`.
- `curl http://localhost:8000/docs` → le Swagger doit afficher `1.2.0`.

**Risques** : Très faible. La fonction `_read_version` a un fallback `"0.0.0"` si le fichier est absent.

---

### Étape 2 — Correction log spam backend (Lot 2 partie backend, P0)

**Objectif** : Réduire le niveau de log des endpoints de polling à DEBUG.

**Fichiers** :
- `backend/api/main.py` (modifier, ~5 lignes)

**Détails d'implémentation** :
1. Dans `request_logging_middleware`, ajouter un set `_quiet_log_paths` contenant `/progress/index/status`.
2. Si le path est dans ce set, utiliser `logger.debug()` au lieu de `logger.info()`.

**Tests à prévoir** :
- Démarrer le backend, appeler `/progress/index/status` → vérifier qu'aucun log INFO n'apparaît pour cet appel (vérifier dans `data/logs/`).
- Vérifier que les autres endpoints continuent de logger en INFO.

**Risques** : Faible. Si le set est vide ou le path mal normalisé, le comportement existant est préservé.

---

### Étape 3 — Correction polling frontend (Lot 2 partie frontend, P0)

**Objectif** : Remplacer le `setInterval` manuel par une query React Query avec `refetchInterval`, et éviter le polling inutile.

**Fichiers** :
- `frontend/src/app/progress/page.tsx` (modifier, ~50 lignes)
- `frontend/src/hooks/useProgress.ts` (ajouter le hook `useProgressIndexStatus` si absent)

**Détails d'implémentation** :
1. Créer ou vérifier l'existence du hook `useProgressIndexStatus` dans `useProgress.ts` :
```tsx
export function useProgressIndexStatus() {
  return useQuery({
    queryKey: ['progress', 'index-status'],
    queryFn: () => progressApi.indexStatus(),
    staleTime: 2_000,
    refetchInterval: (query) => query.state.data?.running ? 2_000 : false,
  });
}
```
2. Dans `progress/page.tsx`, remplacer le `useEffect` + `setInterval` + `useState` par l'utilisation de `useProgressIndexStatus`.
3. Remplacer `queryClient.invalidateQueries({ queryKey: ['progress'] })` par des invalidations ciblées par sous-groupe de clés.
4. Supprimer les refs `indexationStartedRef`, `lastIndexationRefreshAtRef` et le state `indexationState` (remplacés par la query).

**Tests à prévoir** :
- `cd frontend && npm test` — les tests existants de la page Progress doivent passer.
- Vérification manuelle : ouvrir `/progress`, constater qu'aucun polling n'est lancé si l'indexation est déjà faite.
- Vérifier les logs backend : plus de lignes `GET /progress/index/status` en continu.

**Risques** : Moyen. Le `useEffect` actuel a une logique complexe (fallback timeout, refs, indexation auto). La migration vers React Query doit préserver le comportement exact : lancer l'indexation rapide au montage, puis afficher la progression.

---

### Étape 4 — Optimisation cache React Query (Lot 1, P1)

**Objectif** : Configurer un `staleTime` global de 30s et un `gcTime` de 30min.

**Fichiers** :
- `frontend/src/app/providers.tsx` (modifier, ~3 lignes)

**Détails d'implémentation** :
1. Ajouter `staleTime: 30 * 1000` dans `defaultOptions.queries`.
2. Ajouter `gcTime: 30 * 60 * 1000` dans `defaultOptions.queries`.
3. Vérifier que tous les hooks ont un `staleTime` explicite ≥ 30s (sinon, ils héritent du défaut 30s).

**Fichiers à vérifier (lecture seule)** :
- `frontend/src/hooks/useActivity.ts`
- `frontend/src/hooks/useProgress.ts`
- `frontend/src/hooks/useGoals.ts`
- `frontend/src/hooks/useTraces.ts`
- `frontend/src/hooks/useSettings.ts`
- `frontend/src/hooks/useGeo.ts`

**Tests à prévoir** :
- `cd frontend && npm test` — vérifier que les tests passent (certains tests mockent les timers).
- `cd frontend && npm run build` — le build doit réussir.
- Vérification manuelle : naviguer entre les pages, constater via les DevTools Network que les requêtes sont servies depuis le cache (pas de refetch).

**Risques** : Faible. Les `staleTime` explicites par hook (1min, 5min, 10min) écrasent le défaut global. Le défaut global de 30s ne fait que couvrir les queries sans `staleTime`.

---

### Étape 5 — Extraction du helper db_session_factory (Lot 3 partie 1, P1)

**Objectif** : Éliminer les 16+ répétitions du pattern `db_session_factory` dans les routes.

**Fichiers** :
- `backend/api/_helpers.py` (créer)
- `backend/api/routes/progress.py` (modifier, ~50 lignes supprimées)
- `backend/api/routes/settings.py` (modifier, ~10 lignes)
- `backend/api/routes/garmin_integration.py` (modifier, ~8 lignes)
- `backend/api/routes/activities.py` (modifier, ~3 lignes)
- `backend/api/routes/traces.py` (modifier, ~5 lignes — remplacer le helper local)

**Détails d'implémentation** :
1. Créer `backend/api/_helpers.py` avec `get_db_session_factory(request)`.
2. Dans chaque fichier de routes, remplacer le pattern dupliqué par l'import et l'appel.
3. Dans `traces.py`, remplacer le helper local `_get_db_session_factory` par l'import partagé.

**Tests à prévoir** :
- `python -m compileall backend` — doit passer.
- `python -m pytest tests/pytest/ -x -q` — les tests d'intégration doivent passer.
- `python -m pytest tests/unit/ -x -q` — les tests unitaires doivent passer.

**Risques** : Faible. Le helper est identique au pattern existant. Aucun changement de comportement.

---

### Étape 6 — Découpage de metrics.py (Lot 3 partie 2, P2)

**Objectif** : Découper `compute_garmin_like_stats` (415 lignes) en sous-fonctions privées.

**Fichiers** :
- `backend/core/metrics.py` (modifier, restructuration interne)

**Détails d'implémentation** :
1. Extraire `_compute_hr_stats(df, hr_max, hr_rest)` → stats FC (zones, moyenne, max).
2. Extraire `_compute_pace_stats(df, pace_zones)` → stats allure (zones, paces).
3. Extraire `_compute_power_stats(df, ftp)` → stats puissance.
4. Extraire `_compute_cadence_stats(df)` → stats cadence.
5. Extraire `_compute_training_load(df, hr_max, hr_rest)` → TRIMP, charge.
6. `compute_garmin_like_stats` devient un orchestrateur (~30 lignes) qui appelle les sous-fonctions et assemble le résultat.

**Contrainte** : Le dictionnaire retourné doit être **strictement identique** (mêmes clés, mêmes types, mêmes valeurs). Tests de non-régression obligatoires.

**Tests à prévoir** :
- `python -m pytest tests/unit/test_metrics.py -x -v` (ou créer ce fichier s'il n'existe pas).
- Test de non-régression : comparer la sortie de `compute_garmin_like_stats` avant/après sur un DF de référence.
- `python -m pytest tests/pytest/ -x -q` — tests d'intégration.

**Risques** : Moyen. La fonction est critique (utilisée par l'analyse réelle). Le découpage doit être validé par des tests comparatifs. Ne PAS changer la signature publique.

---

### Étape 7 — Découpage de indexer.py (Lot 3 partie 3, P2)

**Objectif** : Découper `index_activity` (379 lignes) en sous-fonctions privées.

**Fichiers** :
- `backend/progress/indexer.py` (modifier, restructuration interne)

**Détails d'implémentation** :
1. Extraire `_classify_and_tag(session, df, meta, activity_id)` → classification d'activité + tags auto.
2. Extraire `_compute_progress_bins(session, df, activity_id, hr_max)` → bins HR/pace.
3. Extraire `_persist_progress_index(session, index_row, zones, splits, climbs, ...)` → écriture DB.
4. `index_activity` devient un orchestrateur (~30 lignes).

**Contrainte** : Même principe que metrics.py — sortie strictement identique.

**Tests à prévoir** :
- Tests existants dans `tests/pytest/test_progress_indexation.py` (ou similaire).
- `python -m pytest tests/pytest/ -x -q -k progress`.

**Risques** : Moyen. L'indexation est une opération sensible (données persistées). Bien vérifier le rollback en cas d'erreur.

---

## 7. Tests et vérifications attendus

### Backend

```bash
# Vérification syntaxe
python -m compileall backend

# Tests unitaires
python -m pytest tests/unit/ -x -q

# Tests d'intégration
python -m pytest tests/pytest/ -x -q

# Vérification spécifique version
python -c "from backend.api.main import _APP_VERSION; assert _APP_VERSION == '1.2.0', f'Expected 1.2.0, got {_APP_VERSION}'; print('OK:', _APP_VERSION)"

# Vérification endpoint racine
curl -s http://localhost:8000/ | python -c "import sys,json; d=json.load(sys.stdin); assert d['version']=='1.2.0'"
```

### Frontend

```bash
cd frontend
npm test
npm run build
npm run lint
```

### Vérifications manuelles

- [ ] Naviguer Accueil → Progression → Accueil → Progression : vérifier dans les DevTools Network que les queries Progress sont servies depuis le cache (pas de refetch si < 1min).
- [ ] Ouvrir Progression quand l'indexation est déjà faite : vérifier qu'aucun polling `/progress/index/status` n'est lancé.
- [ ] Vérifier `data/logs/backend_*.log` : plus de spam `GET /progress/index/status`.
- [ ] Changer `VERSION` de `1.2.0` à `1.2.0-test`, redémarrer le backend, vérifier que `curl localhost:8000/` renvoie `1.2.0-test`. Revenir à `1.2.0`.
- [ ] Vérifier que le Swagger (`/docs`) affiche la version correcte.

---

## 8. Critères d'acceptation

### Lot 1 — Cache React Query
- [ ] `staleTime` global = 30s, `gcTime` = 30min dans `providers.tsx`.
- [ ] Navigation entre pages dans un intervalle < 30s ne déclenche pas de refetch pour les queries avec `staleTime` ≥ 30s.
- [ ] `npm test` et `npm run build` passent.
- [ ] Aucune régression visuelle ou fonctionnelle.

### Lot 2 — Log spam
- [ ] Les appels à `/progress/index/status` ne génèrent PLUS de logs INFO dans `data/logs/`.
- [ ] Les autres endpoints continuent de logger en INFO normalement.
- [ ] Le polling s'arrête quand l'indexation est terminée (vérifiable via DevTools Network : plus de requêtes après `running: false`).
- [ ] Le polling s'arrête quand on quitte la page Progression (cleanup du useEffect / query).

### Lot 3 — Monolithes
- [ ] `routes/progress.py` : plus aucune répétition du pattern `getattr(request.app.state, "db_session_factory", None)` — remplacé par l'appel au helper.
- [ ] `metrics.py` : `compute_garmin_like_stats` ≤ 50 lignes (orchestrateur), sous-fonctions privées ≤ 80 lignes chacune.
- [ ] `indexer.py` : `index_activity` ≤ 50 lignes (orchestrateur).
- [ ] Tous les tests backend passent.
- [ ] Aucune modification du contrat API (endpoints, schémas).

### Lot 4 — Version centralisée
- [ ] Le fichier `VERSION` existe à la racine et contient `1.2.0`.
- [ ] `backend/api/main.py` lit la version depuis `VERSION` (pas de hardcodage).
- [ ] `curl localhost:8000/ | jq .version` renvoie `"1.2.0"`.
- [ ] Le script `npm run sync-version` fonctionne (met à jour `package.json` depuis `VERSION`).
- [ ] Changer `VERSION` + redémarrer → la nouvelle version est visible partout.

---

## 9. Risques et garde-fous

- **Risque 1** : Le `staleTime` global de 30s pourrait cacher des queries sans `staleTime` explicite qui nécessitent des données fraîches. **Garde-fou** : Vérifier chaque hook et s'assurer qu'un `staleTime` explicite est défini partout. Les queries de type "statut" (Garmin sync, indexation) doivent garder un `staleTime` court (2-10s).
- **Risque 2** : Le découpage de `compute_garmin_like_stats` pourrait introduire un bug subtil si une sous-fonction modifie le DataFrame en place ou dépend d'un état partagé. **Garde-fou** : Écrire un test de non-régression comparant la sortie avant/après sur le même jeu de données. Revenir au code original si le test échoue.
- **Risque 3** : La migration du `useEffect` + `setInterval` vers `refetchInterval` dans la page Progress pourrait casser le flux d'indexation automatique. **Garde-fou** : Tester les 3 scénarios : (a) indexation déjà faite → pas de polling, (b) indexation en cours → polling + progression, (c) indexation terminée pendant qu'on est sur la page → arrêt du polling + rafraîchissement des données.
- **Risque 4** : Le fichier `VERSION` pourrait être oublié lors d'un déploiement Docker. **Garde-fou** : Ajouter `COPY VERSION /app/VERSION` dans le Dockerfile et documenter dans le README.
- **Risque 5** : Le `CHANGELOG.md` ne sera pas synchronisé automatiquement avec `VERSION`. **Garde-fou** : C'est intentionnel. Le changelog est rédigé manuellement. Documenter dans `docs/documentation_update_runbook.md` la procédure de release (bump VERSION + ajout entrée CHANGELOG).

---

## 10. Décisions prises par agent-brainstorm

- **Décision 1** : Les 4 lots sont indépendants et peuvent être implémentés dans n'importe quel ordre. Priorité recommandée : Lot 4 → Lot 2 → Lot 1 → Lot 3. **Justification** : Lot 4 (version) est le plus simple et sans risque. Lot 2 (log spam) résout un problème visible immédiatement. Lot 1 (cache) améliore la performance globale. Lot 3 (monolithes) est le plus lourd.
- **Décision 2** : Le `staleTime` global est fixé à 30s (pas plus). **Justification** : 30s est un bon compromis — assez long pour éviter les refetchs lors de navigations rapides, assez court pour que les données restent raisonnablement fraîches. Les queries critiques ont déjà leur propre `staleTime` plus long (1-10min).
- **Décision 3** : Le fichier `VERSION` est placé à la racine (pas dans `backend/` ou `frontend/`). **Justification** : C'est la convention standard (utilisée par des projets comme React, Kubernetes, etc.). La racine est accessible depuis tous les contextes (backend, frontend, Docker, CI).
- **Décision 4** : Le découpage de `metrics.py` et `indexer.py` se fait dans le même fichier (sous-fonctions privées), pas dans de nouveaux modules. **Justification** : Réduit le risque de régression. Un split en nouveaux fichiers pourra être fait dans une itération ultérieure si nécessaire.
- **Décision 5** : Le `CHANGELOG.md` n'est pas automatisé. **Justification** : Les entrées de changelog nécessitent un jugement humain (catégorisation Added/Changed/Fixed, description). L'automatisation complète produirait des entrées de faible qualité.
- **Décision 6** : Le helper `get_db_session_factory` va dans `backend/api/_helpers.py` (nouveau fichier). **Justification** : `traces.py` a déjà ce pattern en local. Le centraliser dans `api/_helpers.py` le rend disponible pour toutes les routes sans dépendance circulaire.

---

## 11. Points à ne pas faire

- **NE PAS** modifier `frontend/src/app/layout.tsx` ou `AppShell.tsx` — le problème de cache n'est pas lié à la structure des pages mais à la config React Query.
- **NE PAS** supprimer le `request_logging_middleware` — il est utile pour le debugging. Juste réduire son niveau pour les chemins de polling.
- **NE PAS** splitter `metrics.py` ou `indexer.py` en nouveaux fichiers — rester dans le même module avec des sous-fonctions privées (réduction du risque).
- **NE PAS** modifier les endpoints API, les schémas Pydantic, ou les contrats de service — tous les changements sont internes.
- **NE PAS** changer le comportement du polling dans `MaintenanceSettings.tsx` (page Settings) — ce composant a sa propre logique de polling légitime pour le suivi d'indexation manuelle.
- **NE PAS** toucher à `data/`, `tests/` (sauf ajout de tests), `docs/*.md` (sauf `CHANGELOG.md` manuellement).
- **NE PAS** introduire de nouvelle dépendance Python ou npm.
- **NE PAS** modifier le `staleTime` des queries Garmin (sync status, credentials) — elles nécessitent une fraîcheur élevée.
