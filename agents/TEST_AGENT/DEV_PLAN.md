# CourseScope — Intégration AllureVsPenteChart dans /activities-beta/[ID]

> **Version** : 1.0
> **Date** : 2026-06-25
> **Statut** : Prêt pour implémentation
> **Type de projet** : Amélioration frontend existante (Next.js / React / TypeScript)
> **Dossier cible** : `C:\Users\domin\Documents\Python Scripts\CourseScope\frontend`

---

## 1. Titre du projet

**Intégrer le graphique Allure vs Pente dans la page beta `/activities-beta/[ID]`**

CourseScope — application locale d'analyse d'activités sportives (running) à partir de fichiers GPX/FIT et de données Garmin.

---

## 2. Objectif général

Assurer que le graphique `AllureVsPenteChart` (allure du coureur en fonction de la pente, avec courbe de référence pro) est correctement visible, accessible et esthétique dans la page beta `/activities-beta/[ID]`.

**Constat initial** : le composant est déjà partiellement intégré via le wrapper `PaceVsGradeCard`, importé dans `ActivityBetaPage.tsx` et listé dans `ActivityBetaSubNav.tsx`. La tâche consiste à **vérifier, corriger si nécessaire, et peaufiner** cette intégration.

---

## 3. Contexte et problème à résoudre

- La page historique `/activities/[ID]` affiche `AllureVsPenteChart` dans l'onglet "Climbs" via `MetricsRegistryRenderer`.
- La page beta `/activities-beta/[ID]` est une refonte complète avec un layout vertical (sections scrollables au lieu d'onglets).
- Un wrapper `PaceVsGradeCard` existe déjà dans `components/activity-beta/` et importe `AllureVsPenteChart`.
- L'utilisateur signale que le graphique n'est pas visible — à vérifier (peut être un problème de données, de rendu, ou de découverte).

### Référence d'audit

Fichier : `agents/agent-review/260625.0907.agent-review.md`

Problèmes identifiés pertinents :
- **M-1** : Mélange stats pondérées/non pondérées dans la bande de variabilité (`paceStd` non pondéré vs `paceStdW` pondéré ignoré par le frontend)
- **m-1** : Variable `paceMean` mal nommée (contient la médiane, pas la moyenne)

---

## 4. Utilisateurs cibles

| Utilisateur | Besoin principal | Niveau technique |
|---|---|---|
| Coureur analysant sa sortie | Comprendre comment son allure varie selon la pente | Débutant/intermédiaire |
| Coureur élite | Comparer sa courbe à la référence pro (Kilian) | Expert |

---

## 5. État actuel

| Élément | Constat |
|---|---|
| `AllureVsPenteChart.tsx` | Composant Recharts fonctionnel, prend `activityId` en prop, gère ses propres états (loading/error/empty) |
| `PaceVsGradeCard.tsx` | Wrapper existant dans `components/activity-beta/`, importe et rend `AllureVsPenteChart` |
| `ActivityBetaPage.tsx` | Importe et rend `<PaceVsGradeCard activityId={activityId} />` dans `<section id="allure-pente">` (ligne 89-91) |
| `ActivityBetaSubNav.tsx` | Inclut `{ id: 'allure-pente', label: 'Allure vs Pente' }` dans la navigation |
| Hook `usePaceVsGrade` | React Query, staleTime 10min, endpoint `GET /api/activity/{id}/pace-vs-grade` |
| API backend | Fonctionnel, renvoie `{ bins: [...], pro_ref: [...] }` |

**Synthèse** : L'intégration structurelle existe. Le problème est probablement un défaut d'affichage (données vides, erreur silencieuse, ou problème de rendu CSS).

---

## 6. Hypothèses retenues

| # | Hypothèse | Niveau de certitude | Impact si faux |
|---|---|---|---|
| 1 | Le graphique est fonctionnel dans la page originale `/activities/[ID]` | Élevé | Aucun — c'est l'état connu |
| 2 | Le wrapper `PaceVsGradeCard` est correctement câblé | Moyen | Le bug vient d'ailleurs (hook, API, rendu) |
| 3 | Le problème est un défaut d'affichage (pas de données pour l'activité testée, ou rendu masqué) | Moyen | Peut nécessiter des logs/debug |
| 4 | L'UI de la beta est cohérente et le graphique s'intègre bien visuellement | À vérifier | Peut nécessiter ajustements CSS |

---

## 7. Périmètre fonctionnel

### Fonctionnalités obligatoires

| # | Fonctionnalité | Description | Priorité |
|---|---|---|---|
| 1 | Affichage du graphique | `AllureVsPenteChart` s'affiche dans la page beta quand les données sont disponibles | Haute |
| 2 | États gérés | Loading, erreur, et absence de données traités proprement | Haute |
| 3 | Navigation | La section est accessible via la subnav "Allure vs Pente" | Haute |
| 4 | UI cohérente | Le style s'intègre avec le reste de la page beta (border, padding, typographie) | Haute |

### Fonctionnalités secondaires

| # | Fonctionnalité | Intérêt |
|---|---|---|
| 1 | Afficher `pace_n` (nombre d'échantillons) dans le tooltip | Transparence sur la fiabilité des bins |
| 2 | Ajouter une `ReferenceLine` à `x=0` (transition plat/pente) | Lisibilité |
| 3 | Utiliser `pace_std_w_s_per_km` au lieu de `pace_std_s_per_km` pour la bande de variabilité | Correction M-1 du rapport d'audit |

---

## 8. Points exclus

| Sujet | Raison |
|---|---|
| Modification du backend (`analysis.py`, `real_run_analysis.py`) | Changement frontend uniquement |
| Modification de la page originale `/activities/[ID]` | Hors scope |
| Refonte complète de `AllureVsPenteChart` | Le composant est fonctionnel |
| Ajout à d'autres onglets de la page originale | Non demandé |

---

## 9. Parcours utilisateur

1. L'utilisateur ouvre une activité dans `/activities-beta/[ID]`
2. Il scrolle ou clique sur "Allure vs Pente" dans la subnav
3. Le graphique s'affiche avec :
   - La courbe de son allure par % de pente (ligne noire)
   - La bande de variabilité (zone grise ± écart-type)
   - La courbe de référence pro (pointillés gris)
   - Les points de données (cercles)
4. Au survol d'un point : tooltip avec allure, pente, et référence pro
5. Si pas de données : message "Aucune donnée de pente disponible"
6. Si erreur API : message d'erreur

---

## 10. Architecture cible

```
ActivityBetaPage
  └── section#allure-pente
        └── PaceVsGradeCard (wrapper beta)
              ├── Titre + description
              ├── États loading/error/empty (gérés par PaceVsGradeCard)
              └── AllureVsPenteChart (composant Recharts)
                    ├── usePaceVsGrade(activityId) → React Query
                    ├── ComposedChart (Recharts)
                    │     ├── Area (bande variabilité)
                    │     ├── Line (proPace, pointillés)
                    │     ├── Line (paceMean, plein)
                    │     └── Scatter (points)
                    └── Tooltip personnalisé
```

---

## 11. Arborescence — fichiers concernés

```text
frontend/src/
├── app/activities-beta/[id]/page.tsx          ← wrapper de route (inchangé)
├── components/activity-beta/
│   ├── ActivityBetaPage.tsx                   ← page principale (déjà intègre PaceVsGradeCard)
│   ├── ActivityBetaSubNav.tsx                 ← navigation (inclut déjà "Allure vs Pente")
│   └── PaceVsGradeCard.tsx                    ← wrapper beta du graphique (EXISTANT — à vérifier/améliorer)
├── components/charts/
│   └── AllureVsPenteChart.tsx                 ← composant graphique (inchangé sauf corrections audit)
└── hooks/
    └── useActivity.ts                         ← hook usePaceVsGrade (inchangé)
```

---

## 12. Stack technique

| Élément | Choix |
|---|---|
| Framework | Next.js 15 (App Router) |
| Langage | TypeScript |
| Bibliothèque de charts | Recharts |
| Gestion d'état/data fetching | React Query (`@tanstack/react-query`) |
| Styling | Tailwind CSS |
| API | FastAPI (backend Python) — endpoint `/api/activity/{id}/pace-vs-grade` |

---

## 13. Dépendances

| Dépendance | Usage | Obligatoire | Décision |
|---|---|---|---|
| Recharts | Rendu du `ComposedChart` | Oui | Déjà installé |
| React Query | `usePaceVsGrade` | Oui | Déjà installé |
| `@/hooks/useActivity` | Hook de données | Oui | Existant |
| `@/components/charts/AllureVsPenteChart` | Composant graphique | Oui | Existant |
| `@/lib/metricsFormat` | Formatage paces | Oui | Existant |

---

## 14. Modèles de données

### `PaceVsGradeBin` (API → frontend)

| Champ | Type | Description |
|---|---|---|
| `grade_center` | `float` | Pente médiane du bin (%) |
| `pace_med_s_per_km` | `float` | Allure médiane (s/km) |
| `pace_std_s_per_km` | `float` | Écart-type allure (s/km) |
| `pace_n` | `int` | Nombre de points dans le bin |
| `pro_pace_s_per_km` | `float\|null` | Allure de référence pro interpolée |
| `time_s_bin` | `float` | Temps total passé dans le bin |
| `pace_std_w_s_per_km` | `float` | Écart-type pondéré (à utiliser pour corriger M-1) |

### `BinPoint` (format intermédiaire dans `AllureVsPenteChart`)

| Champ | Source | Description |
|---|---|---|
| `grade` | `grade_center` | Pente du bin |
| `paceMean` | `pace_med_s_per_km` | Allure médiane (⚠️ mal nommée) |
| `paceStd` | `pace_std_s_per_km` | Écart-type |
| `n` | `pace_n` | Taille d'échantillon |
| `proPace` | `pro_pace_s_per_km` | Référence pro |

---

## 15. Flux de données

```
GET /api/activity/{id}/pace-vs-grade
  → React Query (usePaceVsGrade, staleTime: 10min)
    → PaceVsGradeCard (vérifie data.bins)
      → AllureVsPenteChart (transforme en BinPoint[], calcule domaines X/Y)
        → Recharts ComposedChart (rendu SVG)
```

---

## 16. Gestion des erreurs

| État | Composant responsable | Rendu |
|---|---|---|
| Loading | `PaceVsGradeCard` + `AllureVsPenteChart` | "Chargement..." |
| Erreur API | `PaceVsGradeCard` + `AllureVsPenteChart` | "Erreur de chargement." |
| Aucun bin | `PaceVsGradeCard` | "Aucune donnée de pente disponible pour cette activité." |
| Bins vides après filtrage | `AllureVsPenteChart` | `null` (composant invisible) |

---

## 17. Sécurité et confidentialité

- Aucune donnée sensible exposée (données d'allure/pente agrégées)
- L'endpoint API nécessite un `activityId` valide
- Pas de tokens ou credentials dans le frontend

---

## 18. Tests

### Tests manuels

| Scénario | Étapes | Résultat attendu |
|---|---|---|
| Activité avec données de pente | Ouvrir `/activities-beta/[id]` d'une activité avec D+ | Graphique visible dans la section "Allure vs Pente" |
| Activité sans pente (plat) | Ouvrir une activité sans dénivelé | Message "Aucune donnée de pente disponible" |
| Activité sans données FIT | Ouvrir une activité théorique | Message d'absence ou graphique vide |

### Vérifications visuelles

- [ ] La section apparaît dans la subnav
- [ ] Le clic sur "Allure vs Pente" scrolle vers la section
- [ ] Le style est cohérent avec les autres cartes beta (border, radius, padding)
- [ ] Pas de regression sur la page originale `/activities/[ID]`

---

## 19. Critères d'acceptation

| # | Critère | Vérification |
|---|---|---|
| 1 | Le graphique Allure vs Pente est visible dans `/activities-beta/[ID]` pour une activité avec D+ | Test manuel |
| 2 | Les états loading, error, empty sont gérés sans crash | Test manuel |
| 3 | La navigation "Allure vs Pente" fonctionne | Test manuel |
| 4 | L'UI est cohérente avec le design beta | Revue visuelle |
| 5 | Aucune régression sur `/activities/[ID]` | Test manuel |

---

## 20. Risques techniques

| Risque | Probabilité | Impact | Mesure |
|---|---|---|---|
| Le graphique ne s'affiche pas à cause de données vides pour l'activité test | Moyenne | Faible | Vérifier avec plusieurs activités |
| Double rendu du hook (PaceVsGradeCard + AllureVsPenteChart appellent usePaceVsGrade) | Moyenne | Faible | React Query déduplique par queryKey — OK |
| Conflit de cache React Query entre les deux pages | Faible | Faible | Même queryKey → cache partagé, OK |

---

## 21. Améliorations futures

| Idée | Intérêt | Complexité |
|---|---|---|
| Corriger M-1 (utiliser `pace_std_w_s_per_km`) | Bande de variabilité plus précise | Faible |
| Ajouter `pace_n` dans le tooltip | Transparence | Faible |
| Ajouter `ReferenceLine` à x=0 | Lisibilité | Faible |
| Renommer `paceMean` en `paceMedian` dans `BinPoint` | Clarté du code | Faible |

---

## 22. Questions ouvertes

- L'utilisateur a-t-il testé avec une activité qui a du dénivelé ? Les activités plates peuvent n'avoir aucun bin valide.
- Le problème est-il un défaut d'affichage CSS (section masquée, overflow hidden) ?
- Faut-il appliquer les corrections mineures du rapport d'audit (M-1, m-1 à m-5) dans le même lot ?

---

## 23. Checklist de développement

- [ ] Vérifier l'état actuel de l'intégration (PaceVsGradeCard fonctionnel ?)
- [ ] Tester avec une activité ayant du D+
- [ ] Corriger les éventuels bugs d'affichage
- [ ] Vérifier la cohérence UI
- [ ] Vérifier l'absence de régression sur `/activities/[ID]`
- [ ] Mettre à jour PROGRESS.md
