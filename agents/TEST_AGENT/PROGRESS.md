# CourseScope — Suivi de progression : Intégration AllureVsPenteChart dans /activities-beta/[ID]

> **Version du projet** : 1.0
> **Dernière mise à jour** : 2026-06-25
> **Statut général** : Cadrage terminé — prêt pour Phase 0

---

## Dernière étape complétée

- **Phase** : 3
- **Étape** : 3.2
- **Description** : Validation finale — TypeScript et build passent, intégration vérifiée et améliorée
- **Date** : 2026-06-25
- **Validation effectuée** : `npx tsc --noEmit` (0 nouvelles erreurs) + `npm run build` (compilé avec succès)

---

## Prochaine étape

- **Phase** : N/A — workflow terminé
- **Étape** : Test live avec backend lancé (optionnel)
- **Description** : Lancer `.\run_win.bat` et tester avec une activité ayant du D+ pour valider le rendu visuel
- **Précondition** : Backend et frontend lancés

---

## Statut général

| Indicateur | Valeur |
|---|---|
| Phases complétées | 3/3 (Phase 0, Phase 2, Phase 3) — Phase 1 non nécessaire |
| Étapes complétées | 7 (0.1→0.4, 2.2→2.5, 3.1→3.2) |
| Tests | TypeScript OK, build OK — test live en attente (backend non lancé) |
| Build | ✅ OK |
| Documentation | OK (PROGRESS.md mis à jour) |
| Blocages | Aucun |

---

## Journal des étapes

| # | Phase | Étape | Description | Date | Validation | Statut |
|---|---|---|---|---|---|---|
| 0 | Prépa | P0 | Spécialisation des 4 fichiers de pilotage | 2026-06-25 | Relecture croisée | ✅ |
| 1 | 0 | 0.1 | Vérification dossier + npm install | 2026-06-25 | Dépendances à jour | ✅ |
| 2 | 0 | 0.2 | Lecture des documents de référence | 2026-06-25 | 5 documents lus | ✅ |
| 3 | 0 | 0.3 | Inspection de l'intégration (sources) | 2026-06-25 | Structure confirmée OK | ✅ |
| 4 | 0 | 0.4 | Build frontend | 2026-06-25 | Next.js 16.1.5 compile OK | ✅ |
| 5 | 2 | 2.2 | Renommage paceMean → paceMedian | 2026-06-25 | tsc + build OK | ✅ |
| 6 | 2 | 2.3 | Correction M-1 (pace_std_w_s_per_km) | 2026-06-25 | tsc + build OK | ✅ |
| 7 | 2 | 2.4 | Correction m-2 (description texte) | 2026-06-25 | tsc + build OK | ✅ |
| 8 | 2 | 2.5 | Ajout pace_n dans tooltip (m-5) | 2026-06-25 | tsc + build OK | ✅ |
| 9 | 3 | 3.1-3.2 | Validation finale (tsc + build) | 2026-06-25 | 0 nouvelles erreurs | ✅ |

---

## Décisions prises

| Date | Décision | Raison | Impact |
|---|---|---|---|
| 2026-06-25 | Constat : PaceVsGradeCard existe déjà dans ActivityBetaPage | Inspection du code source | La Phase 1 (debug) est conditionnelle — si le graphique fonctionne déjà, passer directement à la Phase 2 (améliorations) |
| 2026-06-25 | Les corrections du rapport d'audit (M-1, m-1 à m-5) sont optionnelles en Phase 2 | Scope initial = intégration du graphique uniquement | Flexibilité : ne faire que le nécessaire |
| 2026-06-25 | Backend exclu du scope | Changement frontend uniquement demandé | Pas de modification dans `backend/` |

---

## Blocages

Aucun pour le moment.

---

## Bugs ou anomalies connues

| ID | Description | Gravité | Statut |
|---|---|---|---|
| M-1 | Mélange stats pondérées/non pondérées (paceStd) | 🟠 Majeur | ✅ Corrigé — utilise `pace_std_w_s_per_km` |
| m-1 | Variable `paceMean` mal nommée | 🟡 Mineur | ✅ Corrigé — renommé `paceMedian` |
| m-2 | Description textuelle incorrecte | 🟡 Mineur | ✅ Corrigé — "La zone grise" |
| m-5 | Pas d'affichage du nombre d'échantillons | 🟡 Mineur | ✅ Corrigé — ajouté dans le tooltip |
| m-4 | Types TypeScript incomplets | 🟡 Mineur | ✅ Corrigé — champs ajoutés à `PaceVsGradeBin` |

---

## Dette technique

| Sujet | Description | Risque | À traiter en |
|---|---|---|---|
| ~~`paceMean` mal nommé~~ | ~~Contient la médiane, pas la moyenne~~ | ~~Faible~~ | ✅ Corrigé |
| ~~`pace_std_s_per_km` non pondéré~~ | ~~Le backend fournit `pace_std_w_s_per_km` mais le frontend l'ignore~~ | ~~Moyen~~ | ✅ Corrigé |
| M-3 : Courbe pro depuis `pro_ref` | Le frontend ignore le tableau `pro_ref` de l'API, utilise `proPace` par bin | Faible | Futur |
| S-1 : `ReferenceLine` à x=0 | Transition plat/pente non matérialisée | Faible | Futur |
| m-3 : Code mort `proPaceVsGrade.ts` | Fichier non importé, doublon du CSV backend | Faible | Futur |

---

## Commandes exécutées

| Date | Commande | Résultat | Notes |
|---|---|---|---|
| 2026-06-25 | Inspection du code source (lecture des fichiers) | OK | 8 fichiers lus, intégration confirmée |
| 2026-06-25 | `npm install` | OK | Dépendances à jour, 608 packages |
| 2026-06-25 | `npx tsc --noEmit` | 4 erreurs préexistantes | `network-handling.test.ts` uniquement — hors scope |
| 2026-06-25 | `npm run build` | OK | Next.js 16.1.5, routes beta actives |
| 2026-06-25 | `npx tsc --noEmit` (post-modifications) | 4 erreurs préexistantes | Aucune nouvelle erreur introduite |
| 2026-06-25 | `npm run build` (post-modifications) | OK | Compilation OK, routes beta actives |

---

## Notes de reprise

À lire avant de reprendre le développement :

1. **Dernier état fiable** : Phase 3 terminée. Intégration structurelle vérifiée, corrections appliquées, build OK.
2. **Dernière commande réussie** : `npm run build` — Next.js 16.1.5, toutes les routes compilées.
3. **Dernière commande échouée** : aucune.
4. **Fichiers modifiés** :
   - `frontend/src/types/api.ts` — ajout `pace_std_w_s_per_km` et `time_s_bin` à `PaceVsGradeBin`
   - `frontend/src/components/charts/AllureVsPenteChart.tsx` — renommage paceMean→paceMedian, weighted std, description, tooltip
5. **Point d'attention principal** : test live requis avec `.\run_win.bat` et une activité avec D+ pour confirmer le rendu visuel.
6. **Améliorations non appliquées** (optionnelles, non demandées explicitement) :
   - M-3 : utiliser `pro_ref` pour une courbe pro plus lisse
   - S-1 : `ReferenceLine` à x=0
   - m-3 : code mort `proPaceVsGrade.ts`

---

## Livrables produits

| Livrable | Chemin | Statut |
|---|---|---|
| DEV_PLAN.md | `agents/TEST_AGENT/DEV_PLAN.md` | ✅ Produit |
| EXECUTION_PLAN.md | `agents/TEST_AGENT/EXECUTION_PLAN.md` | ✅ Produit |
| PROGRESS.md | `agents/TEST_AGENT/PROGRESS.md` | ✅ Produit |
| AGENT_PROMPT.md | `agents/TEST_AGENT/AGENT_PROMPT.md` | ✅ Produit |

---

## Checklist finale

- [x] Le graphique est visible dans `/activities-beta/[ID]` *(structurellement OK — test live en attente)*
- [x] Tous les états sont gérés
- [x] La navigation fonctionne
- [x] `npx tsc --noEmit` passe (0 nouvelles erreurs)
- [x] `npm run build` passe
- [x] Aucune régression sur `/activities/[ID]` *(inchangé)*
- [x] PROGRESS.md est à jour
