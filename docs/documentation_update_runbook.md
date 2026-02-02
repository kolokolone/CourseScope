# Documentation update runbook

NE PAS MODIFIER CE FICHIER.
Suivre ces etapes uniquement quand je te le demande.

Objectif: garder une documentation reproductible apres chaque changement backend/frontend.

## Regles

- Ne pas modifier les fichiers `docs/*.md` (autres que ceux explicitement demandes) sans autorisation.
- Toujours documenter les changements proportionnellement:
  - README: vue d'ensemble, liens, commandes de lancement
  - CHANGELOG: liste des changements user-facing
  - docs/*: details techniques, contrats, algorithmes
- Ne pas casser l'API: toute nouvelle metrique doit etre optionnelle ou compatible.

## Procedure

1) Audit des metriques
- Lire `backend/api/routes/analysis.py` et lister toutes les cles/paths renvoyees.
- Verifier les schemas dans `backend/api/schemas.py`.
- Verifier les generateurs core (ex: `backend/core/real_run_analysis.py`).

2) Mettre a jour le catalog
- Mettre a jour `docs/metrics_catalog.md`:
  - ajouter les nouvelles metriques
  - modifier celles dont le contrat a change
  - conserver le schema/tableaux existants.

3) Mettre a jour la liste file-only
- Mettre a jour `docs/metrics_list.txt`:
  - ajouter/retirer les paths
  - garder le format (sections numerotees, labels [Both]/[FIT]/[Cond ...]).

4) Mettre a jour les autres docs (si demande)
- README: seulement si la navigation/commande/definition a change.
- CHANGELOG: toujours ajouter une entree pour la version.
- Autres docs (ex: cahier_des_charges): uniquement si le fichier existe et si demande.

5) Verification
- Backend: `python -m pytest -q`
- Frontend: `npm test` et `npm run build` (dans `frontend/`)
- Noter explicitement les erreurs pre-existantes si elles ne sont pas liees.

6) Version bump
- Determiner la derniere version sur `origin/main`.
- Bumper en patch (vX.Y.Z -> vX.Y.(Z+1)) sauf demande contraire.
- Appliquer le bump au minimum dans:
  - `backend/api/main.py`
  - `frontend/package.json`
  - `CHANGELOG.md`

7) Commit + push
- Stage uniquement les fichiers lies au lot.
- Commit message clair: `vX.Y.Z: <objectif>`.
- Push sur `origin/main`.
