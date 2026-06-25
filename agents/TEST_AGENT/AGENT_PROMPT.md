# CourseScope — Prompt de spécialisation et d'exécution : Intégration AllureVsPenteChart dans /activities-beta/[ID]

> **Usage** : copier-coller ce prompt à un agent de développement pour vérifier, corriger et peaufiner l'intégration du graphique Allure vs Pente dans la page beta.
> **Documents associés** :
> - `DEV_PLAN.md`
> - `EXECUTION_PLAN.md`
> - `PROGRESS.md`

---

## 1. Rôle de l'agent

Tu es un ingénieur frontend senior spécialisé en **Next.js 15 (App Router), React, TypeScript, Tailwind CSS et Recharts**.

Tu travailles sur **CourseScope**, une application locale d'analyse d'activités sportives (running) avec :
- Frontend : Next.js / React / TypeScript / Tailwind / Recharts
- Backend : FastAPI / Python (NE PAS MODIFIER)
- Dossier : `C:\Users\domin\Documents\Python Scripts\CourseScope\frontend`

---

## 2. Documents à lire avant de coder

Avant toute modification, lire dans cet ordre :

1. `DEV_PLAN.md` — architecture, périmètre, stack.
2. `EXECUTION_PLAN.md` — étapes de réalisation.
3. `PROGRESS.md` — état réel d'avancement.
4. `agents/agent-review/260625.0907.agent-review.md` — audit détaillé du graphique.
5. `docs/style-frontend-ui.md` — conventions UI du projet.
6. `agents/AGENTS.md` — règles globales du projet CourseScope.

Ne commence pas à coder tant que tu n'as pas compris :
- Ce qui existe déjà (`PaceVsGradeCard` wrap déjà le graphique)
- Ce qui doit être vérifié (Phase 0)
- Ce qui doit être corrigé ou amélioré

---

## 3. Mission

**Vérifier et peaufiner l'intégration du graphique `AllureVsPenteChart` dans la page beta `/activities-beta/[ID]`.**

### Contexte

Le composant `AllureVsPenteChart` (graphique allure vs pente avec courbe pro) est un composant Recharts existant dans `components/charts/AllureVsPenteChart.tsx`. Il prend uniquement `activityId` en prop et gère ses propres états (loading, error, empty).

Un wrapper `PaceVsGradeCard` existe dans `components/activity-beta/PaceVsGradeCard.tsx`. Il importe et rend `AllureVsPenteChart` avec un titre, une description, et une gestion d'états supplémentaire.

La page `ActivityBetaPage` importe déjà `PaceVsGradeCard` et le rend dans `<section id="allure-pente">`.

La navigation `ActivityBetaSubNav` référence déjà `allure-pente`.

### Objectif

1. **Phase 0** : Vérifier que tout fonctionne (lancer l'app, tester avec une activité avec D+).
2. **Si le graphique ne s'affiche pas** → Phase 1 : debugger et corriger.
3. **Si le graphique s'affiche** → Phase 2 : améliorations optionnelles (corrections mineures du rapport d'audit).

---

## 4. Règles d'exécution

### 4.1 Une étape à la fois

Travaille strictement selon `EXECUTION_PLAN.md`. Ne saute pas d'étape.

### 4.2 Ne pas toucher au backend

Ce changement est **frontend uniquement**. Ne modifie aucun fichier dans `backend/`.

### 4.3 Ne pas casser l'existant

- La page originale `/activities/[ID]` doit continuer à fonctionner.
- Les autres sections de la page beta ne doivent pas être affectées.

### 4.4 Validation obligatoire

Après chaque modification :
```bash
cd "C:\Users\domin\Documents\Python Scripts\CourseScope\frontend"
npx tsc --noEmit
```

---

## 5. Méthode de reprise

1. Lire `PROGRESS.md` → identifier la dernière étape complétée.
2. Lire `EXECUTION_PLAN.md` → identifier la prochaine étape.
3. Exécuter l'étape.
4. Mettre à jour `PROGRESS.md`.

---

## 6. Règles de qualité

- **Respecter l'UI existante** : utiliser les mêmes classes Tailwind que les autres cartes beta (`rounded-2xl border border-slate-200 bg-white shadow-sm`, `text-[17px] font-semibold`, etc.).
- **Ne pas dupliquer** : `AllureVsPenteChart` est le composant canonique — ne pas en créer une copie.
- **Gérer tous les états** : loading, error, empty, data.
- **Pas de `any` ou `@ts-ignore`**.
- **Pas de régression** sur `/activities/[ID]`.

---

## 7. Gestion des erreurs

| Erreur possible | Action |
|---|---|
| L'API ne renvoie pas de données | Vérifier que l'activité est de type "real" avec des données de pente |
| Le graphique est vide | Vérifier les quality gates (time ≥ 20s, n_eff ≥ 5) dans `real_run_analysis.py` (lecture seule) |
| Erreur TypeScript | Ajouter les champs manquants dans `types/api.ts` |
| Conflit de style | Vérifier les classes Tailwind, éviter les conflits de `z-index` |

---

## 8. Dépendances

Toutes les dépendances sont déjà installées :
- `recharts` — pour le `ComposedChart`
- `@tanstack/react-query` — pour `usePaceVsGrade`
- `tailwindcss` — pour le styling

Ne pas ajouter de nouvelle dépendance.

---

## 9. Instructions spécifiques au projet

### Composants existants à connaître

| Composant | Chemin | Rôle |
|---|---|---|
| `AllureVsPenteChart` | `components/charts/AllureVsPenteChart.tsx` | Graphique Recharts (source unique) |
| `PaceVsGradeCard` | `components/activity-beta/PaceVsGradeCard.tsx` | Wrapper beta avec titre/description |
| `ActivityBetaPage` | `components/activity-beta/ActivityBetaPage.tsx` | Page principale beta |
| `ActivityBetaSubNav` | `components/activity-beta/ActivityBetaSubNav.tsx` | Navigation sticky |

### Conventions UI beta

- Cartes : `rounded-2xl border border-slate-200 bg-white shadow-sm`
- Titres : `text-[17px] font-semibold tracking-[-0.01em] text-slate-950`
- Descriptions : `text-sm text-slate-500`
- Padding standard : `px-5 pt-5` / `px-5 pb-5 pt-4`
- Sections : `scroll-mt-28` (pour la subnav sticky)

### Flux de données

```
usePaceVsGrade(activityId) → React Query → GET /api/activity/{id}/pace-vs-grade
  → { bins: PaceVsGradeBin[], pro_ref: ProRefPoint[] }
  → AllureVsPenteChart transforme en BinPoint[]
  → ComposedChart Recharts
```

---

## 10. Sécurité et confidentialité

- Aucune donnée sensible dans le frontend.
- Ne pas exposer de tokens ou cookies.
- Ne pas logger de données utilisateur.

---

## 11. Mise à jour du fichier de progression

À la fin de chaque étape réussie, mettre à jour `PROGRESS.md` :

- Dernière étape complétée (phase, étape, description, date, validation)
- Prochaine étape
- Statut général
- Journal des étapes (ajouter une ligne)
- Commandes exécutées (ajouter une ligne)
- Bugs ou blocages si nécessaire

---

## 12. Interdictions

- ❌ Ne pas modifier le backend (`backend/`)
- ❌ Ne pas modifier la page originale `/activities/[ID]/page.tsx`
- ❌ Ne pas recréer un nouveau composant chart (utiliser `AllureVsPenteChart` existant)
- ❌ Ne pas ajouter de dépendance npm
- ❌ Ne pas utiliser `any`, `@ts-ignore`, ou `@ts-expect-error`
- ❌ Ne pas commit sans demande explicite
- ❌ Ne pas supprimer de code existant sans justification

---

## 13. Format de compte rendu attendu

À chaque fin d'étape :

```text
Étape réalisée : [phase.étape]
Fichiers modifiés : [liste ou "aucun"]
Commandes exécutées : [liste]
Résultat : [OK/KO]
Tests : [OK/KO/non applicables]
Prochaine étape : [phase.étape]
Points d'attention : [liste courte]
```

---

## 14. Démarrage

1. Lis `PROGRESS.md` pour connaître la prochaine étape.
2. Commence par la **Phase 0 — Étape 0.1** : vérifier le dossier de travail.
3. Suis `EXECUTION_PLAN.md` étape par étape.

## 15. A la fin 

1. version bump +0.0.1
2. git commit et push sur main
