# CourseScope — Plan d'exécution : Intégration AllureVsPenteChart dans /activities-beta/[ID]

> **Version** : 1.0
> **Date** : 2026-06-25
> **Statut** : Guide de réalisation pas-à-pas
> **Dépend de** : `DEV_PLAN.md`

---

## Objectif du document

Ce fichier détaille les étapes pour vérifier, corriger et peaufiner l'intégration du graphique Allure vs Pente dans la page beta de CourseScope.

---

## Règles générales d'exécution

1. Travailler une étape à la fois.
2. Ne pas modifier le backend (changement frontend uniquement).
3. Ne pas toucher à la page originale `/activities/[ID]`.
4. Vérifier visuellement après chaque modification.
5. Toute divergence avec le plan doit être notée dans `PROGRESS.md`.

---

## Commandes de validation

```bash
# Depuis le dossier frontend
cd "C:\Users\domin\Documents\Python Scripts\CourseScope\frontend"

# Vérification TypeScript
npx tsc --noEmit

# Build de vérification
npm run build

# Lint
npm run lint

# Tests (si existants pour les composants modifiés)
npm test
```

---

## Structure finale cible du projet

```text
frontend/src/
├── app/activities-beta/[id]/page.tsx          ← inchangé
├── components/activity-beta/
│   ├── ActivityBetaPage.tsx                   ← inchangé (déjà OK)
│   ├── ActivityBetaSubNav.tsx                 ← inchangé (déjà OK)
│   └── PaceVsGradeCard.tsx                    ← PEUT ÊTRE MODIFIÉ (améliorations UI/états)
├── components/charts/
│   └── AllureVsPenteChart.tsx                 ← PEUT ÊTRE MODIFIÉ (corrections mineures audit)
└── hooks/
    └── useActivity.ts                         ← inchangé
```

---

## Phase 0 — Audit et état de référence

> **Objectif** : vérifier ce qui fonctionne, ce qui ne fonctionne pas, et établir un état de référence avant toute modification.

### Étape 0.1 — Vérifier le dossier de travail

- Confirmer le chemin : `C:\Users\domin\Documents\Python Scripts\CourseScope\frontend`
- Vérifier que `node_modules` est installé : `npm install`

**Commande** :
```bash
npm install
```

**Résultat attendu** : dépendances à jour, pas d'erreur.

---

### Étape 0.2 — Lire les documents de référence

Lire dans cet ordre :
1. `DEV_PLAN.md` (ce dossier)
2. `PROGRESS.md` (ce dossier)
3. `agents/agent-review/260625.0907.agent-review.md` (rapport d'audit)
4. `docs/style-frontend-ui.md` (conventions UI)

**Résultat attendu** : compréhension du périmètre et des contraintes.

---

### Étape 0.3 — Vérifier l'état actuel de l'intégration

Inspecter les fichiers existants :

```bash
# Vérifier les imports
grep -r "AllureVsPenteChart" src/components/activity-beta/
grep -r "PaceVsGradeCard" src/components/activity-beta/
```

**Checklist** :
- [ ] `PaceVsGradeCard.tsx` importe `AllureVsPenteChart`
- [ ] `ActivityBetaPage.tsx` importe et rend `PaceVsGradeCard`
- [ ] `ActivityBetaSubNav.tsx` référence `allure-pente`
- [ ] La section a `id="allure-pente"` avec `scroll-mt-28`

---

### Étape 0.4 — Lancer l'application et tester

```bash
# Depuis la racine du projet
.\run_win.bat
```

- Ouvrir `http://localhost:3000/activities-beta/[ID]` avec un ID d'activité ayant du dénivelé.
- Vérifier que la section "Allure vs Pente" est visible.
- Vérifier les états : loading, données, erreur.

**Si le graphique s'affiche correctement** : passer à la Phase 2 (améliorations).
**Si le graphique ne s'affiche pas** : passer à la Phase 1 (debug).

---

### Fin Phase 0 — Livrables

| Livrable | Statut |
|---|---|
| Dossier projet vérifié | ☐ |
| Documents lus | ☐ |
| État initial constaté | ☐ |
| Prochaine phase déterminée (1 ou 2) | ☐ |

---

## Phase 1 — Debug et correction (si le graphique ne s'affiche PAS)

> **Objectif** : identifier la cause du non-affichage et corriger.

### Étape 1.1 — Vérifier les données API

- Ouvrir les DevTools (F12) → Network
- Vérifier l'appel à `/api/activity/{id}/pace-vs-grade`
- Code HTTP attendu : 200
- Corps de réponse attendu : `{ bins: [...], pro_ref: [...] }`

**Si 404 ou erreur** : le backend ne sert pas cet endpoint pour cette activité. Vérifier que l'activité est de type "real" (pas "theoretical").

**Si 200 mais `bins` vide** : l'activité n'a pas assez de données de pente (plat, ou données insuffisantes après quality gates).

---

### Étape 1.2 — Vérifier le hook React Query

- Vérifier que `usePaceVsGrade(activityId)` est appelé avec le bon `activityId`.
- Utiliser React Query DevTools pour inspecter l'état du cache.

**Points de contrôle dans `PaceVsGradeCard.tsx`** :
```typescript
const { data, isLoading, error } = usePaceVsGrade(activityId);
// data?.bins doit être un tableau
// data?.bins.length > 0 pour afficher le graphique
```

---

### Étape 1.3 — Vérifier le rendu conditionnel

Dans `PaceVsGradeCard.tsx`, vérifier la logique :
```typescript
{isLoading && <div>Chargement...</div>}
{error && <div>Erreur de chargement.</div>}
{!isLoading && !error && !hasBins && <div>Aucune donnée...</div>}
{hasBins && <AllureVsPenteChart activityId={activityId} />}
```

**Problème potentiel** : `hasBins` est `false` même si l'API renvoie des données → vérifier `data?.bins?.length`.

---

### Étape 1.4 — Vérifier le CSS

- Inspecter la section `#allure-pente` dans les DevTools
- Vérifier qu'elle n'est pas masquée (`display: none`, `visibility: hidden`, `height: 0`, `overflow: hidden`)
- Vérifier le `scroll-mt-28` et le `z-index` de la subnav sticky

---

### Étape 1.5 — Test avec une activité connue

Utiliser une activité qui fonctionne dans `/activities/[ID]` (onglet Climbs) et tester la même dans `/activities-beta/[ID]`.

---

## Phase 2 — Améliorations et polish

> **Objectif** : peaufiner l'intégration pour une UI cohérente et appliquer les corrections mineures du rapport d'audit.

### Étape 2.1 — Vérifier la cohérence UI

Comparer le style de `PaceVsGradeCard` avec les autres cartes beta (`ActivitySummaryCard`, `KeyIndicatorsCard`, etc.) :

| Élément | Attendu |
|---|---|
| Container | `rounded-2xl border border-slate-200 bg-white shadow-sm` |
| Titre | `text-[17px] font-semibold tracking-[-0.01em] text-slate-950` |
| Description | `text-sm text-slate-500` |
| Padding | `px-5 pt-5` / `px-5 pb-5 pt-4` |

---

### Étape 2.2 — (Optionnel) Corriger le nommage `paceMean` → `paceMedian`

**Fichier** : `AllureVsPenteChart.tsx`

Renommer `paceMean` en `paceMedian` dans `BinPoint` et toutes les références (dataKey Recharts, tooltip, calculs). Ce changement est cosmétique mais améliore la maintenabilité.

**Risque** : renommage de `dataKey` dans Recharts — vérifier que les graphiques s'affichent toujours.

---

### Étape 2.3 — (Optionnel) Utiliser `pace_std_w_s_per_km` pour la bande de variabilité

**Fichier** : `AllureVsPenteChart.tsx`, ligne 73-74

Remplacer :
```typescript
paceStd: b.pace_std_s_per_km,
```
par :
```typescript
paceStd: b.pace_std_w_s_per_km ?? b.pace_std_s_per_km,
```

**Fichier** : `types/api.ts` — si `pace_std_w_s_per_km` n'est pas dans le type, l'ajouter comme champ optionnel.

---

### Étape 2.4 — (Optionnel) Ajouter `pace_n` dans le tooltip

**Fichier** : `AllureVsPenteChart.tsx`, fonction `AllureVsPenteTooltip`

Ajouter une ligne :
```tsx
<div className="text-muted-foreground">{`Échantillons: ${p.n}`}</div>
```

---

### Étape 2.5 — Vérification post-modifications

```bash
npx tsc --noEmit
npm run build
```

- Ouvrir `/activities-beta/[ID]` et vérifier le graphique.
- Ouvrir `/activities/[ID]` (onglet Climbs) et vérifier l'absence de régression.

---

## Phase 3 — Validation finale

### Étape 3.1 — Tests manuels

| # | Scénario | Résultat attendu |
|---|---|---|
| 1 | Activité avec D+ | Graphique visible avec courbes |
| 2 | Activité plate | Message "Aucune donnée" |
| 3 | Clic subnav "Allure vs Pente" | Scroll fluide vers la section |
| 4 | Page originale `/activities/[ID]` | Aucune régression |

### Étape 3.2 — Checklist

- [ ] `npx tsc --noEmit` passe
- [ ] `npm run build` passe
- [ ] Tous les états (loading/error/empty/data) sont gérés
- [ ] UI cohérente avec le reste de la page beta
- [ ] `PROGRESS.md` mis à jour

---

## Conduite à tenir en cas d'échec

| Échec | Action |
|---|---|
| L'API ne renvoie pas de données | Vérifier que l'activité a des données de pente (colonnes `elevation`, `delta_distance_m` dans le fichier source) |
| Le graphique s'affiche mais est coupé | Vérifier le `ResponsiveContainer` et la hauteur `h-72` |
| Conflit de cache React Query | Le cache est partagé par queryKey — normal. Rafraîchir si nécessaire. |
| Erreur TypeScript après modification | Vérifier les types dans `types/api.ts` |
