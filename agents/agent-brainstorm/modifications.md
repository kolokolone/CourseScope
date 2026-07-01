# Modifications à implémenter — CourseScope

Date : 2026-07-01 13:15
Source : agents/modifications.txt
Produit par : agents/agent-brainstorm.md
Statut : prêt pour agent-dev

## 1. Résumé exécutif

Deux correctifs d'infrastructure (ops) sans impact sur le code applicatif :

1. **Node 20 → Node 22** dans le Dockerfile (2 occurrences) et la CI (1 occurrence). Node 22 est LTS, résout le warning EBADENGINE sur `camera-controls` (dépendance transitive de Three.js), et le README recommande déjà Node 22.
2. **Sécurisation des vulnérabilités npm** : ajout d'un `npm audit fix --production` avant le build Docker + blocage du build si une vulnérabilité high/critical persiste.

Aucun changement de code frontend, backend, tests ou documentation applicative. Les deux modifications sont indépendantes et peuvent être exécutées en parallèle.

## 2. Demandes utilisateur extraites

### Demande 1 — Passer Node 20 → Node 22

- **Texte source** : « Remplacer `node:20-bookworm-slim` → `node:22-bookworm-slim` » + « Dans `ci_cd.yml`, passer `node-version: "22"` »
- **Interprétation** : Mettre à jour l'image de base Docker et la version Node utilisée en CI de Node 20 vers Node 22.
- **Statut** : **retenue**
- **Justification** : Node 22 est LTS (octobre 2025), compatible avec Next.js 16.1.5, et résout le warning EBADENGINE sur `camera-controls@3.1.2` qui requiert Node >=22. Le README mentionne déjà « Node.js 20+ (22 recommandé) ». Node 24 n'est pas encore LTS — passer directement en 24 serait prématuré.

### Demande 2 — Traiter les vulnérabilités npm proprement

- **Texte source** : « Ajouter dans le Dockerfile après `npm ci` : `npm audit --omit=dev --audit-level=high || exit 1` » + exécuter `npm audit fix --production` en amont.
- **Interprétation** : Ajouter une étape d'audit de sécurité npm dans le pipeline Docker pour bloquer le build en cas de vulnérabilité runtime high/critical. Application des correctifs safe automatiquement.
- **Statut** : **retenue**
- **Justification** : 16 vulnérabilités (1 low, 6 moderate, 8 high, 1 critical) ont été rapportées. Laisser des vulnérabilités high/critical non résolues dans l'image de production est un risque. La procédure proposée est conservative : `audit fix --production` ne change que les correctifs safe (pas de --force), et le blocage à l'étape suivante protège contre les régressions.

## 3. Diagnostic de l'existant

### 3.1 Fichiers et zones lus

- `Dockerfile` — image multi-stage, 2 builds, 2 occurrences de `node:20-bookworm-slim` (lignes 3 et 13)
- `.github/workflows/ci_cd.yml` — CI GitHub Actions, `node-version: "20"` ligne 29
- `frontend/package.json` — dépendances, pas de `overrides` existant
- `README.md` — mentionne déjà « Node.js 20+ (22 recommandé) »
- `agents/modifications.txt` — fichier d'entrée utilisateur
- `docs/style-frontend-ui.md` — consulté (non impacté)

### 3.2 Constats établis

- **Dockerfile ligne 3** : `FROM node:20-bookworm-slim AS web-build` — confirmé.
- **Dockerfile ligne 13** : `FROM node:20-bookworm-slim` — confirmé (image runtime finale).
- **ci_cd.yml ligne 29** : `node-version: "20"` — confirmé.
- **npm ci** dans le Dockerfile : pas d'étape d'audit après l'installation.
- **Pas d'`overrides`** dans `package.json` : les vulnérabilités ne sont pas gérées activement.
- **Next.js 16.1.5** : compatible Node 22 (documenté par Vercel).
- **`camera-controls`** : n'est pas une dépendance directe mais une dépendance transitive (via `@react-three/drei` ou `three`).

### 3.3 Hypothèses

- `npm audit fix --production` résoudra une partie des vulnérabilités sans casser les dépendances.
- Les vulnérabilités résiduelles après `audit fix --production` seront dans des dépendances transitives de Next.js lui-même, non exploitables dans le contexte de l'application (locale, mono-utilisateur).

### 3.4 Incertitudes

- Le nombre exact de vulnérabilités résiduelles après `npm audit fix --production` n'est pas connu sans exécution.
- `camera-controls@3.1.2` est une dépendance transitive — son warning EBADENGINE est peut-être déjà résolu dans une version plus récente (via `npm audit fix --production`).

## 4. Spécification fonctionnelle cible

Sans objet : les deux demandes sont purement infrastructure. Aucun changement de comportement utilisateur.

## 5. Spécification technique proposée

### 5.1 Frontend

Aucun changement.

### 5.2 Backend

Aucun changement.

### 5.3 Infrastructure (Docker + CI)

**Demande 1 : Node 20 → Node 22**

| Fichier | Ligne | Changement |
|---|---|---|
| `Dockerfile` | 3 | `node:20-bookworm-slim` → `node:22-bookworm-slim` |
| `Dockerfile` | 13 | `node:20-bookworm-slim` → `node:22-bookworm-slim` |
| `.github/workflows/ci_cd.yml` | 29 | `node-version: "20"` → `node-version: "22"` |

**Demande 2 : Audit de sécurité npm**

Dans le Dockerfile, après la ligne 7 (`RUN npm ci`) et avant la ligne 9 (`COPY frontend ./`), ajouter :

```dockerfile
RUN npm audit fix --production --omit=dev || echo "audit-fix: continuing"
RUN npm audit --omit=dev --audit-level=high || exit 1
```

Justification du `|| echo` sur la première ligne : `audit fix` peut échouer si toutes les vulnérabilités ne sont pas corrigeables automatiquement, mais on ne veut pas bloquer le build à cette étape — le blocage est fait par la seconde ligne sur les vulnérabilités résiduelles high+.

Le build doit échouer si une vulnérabilité runtime de niveau **high** ou **critical** persiste après correctif automatique.

### 5.4 Documentation

- `README.md` ligne 35 : mettre à jour « Node.js 20+ (22 recommandé) » → « Node.js 22+ ». La mention de Node 20 n'est plus pertinente.
- Pas d'autre documentation à modifier.

## 6. Plan d'implémentation pour agent-dev

### Étape 1 — Mise à jour des images Docker (Node 20 → Node 22)

- **Objectif** : Remplacer les deux occurrences de `node:20-bookworm-slim` par `node:22-bookworm-slim`.
- **Fichiers** : `Dockerfile` (lignes 3 et 13)
- **Détails** : Remplacement textuel. Aucun changement de dépendances système (Debian Bookworm est la même).
- **Tests à prévoir** : `docker build` local pour vérifier que l'image se construit.
- **Risques** : Faible — Node 22 est LTS, compatible avec toutes les dépendances actuelles.

### Étape 2 — Mise à jour de la CI (Node 20 → Node 22)

- **Objectif** : Passer `node-version: "22"` dans la CI GitHub Actions.
- **Fichiers** : `.github/workflows/ci_cd.yml` (ligne 29)
- **Détails** : Remplacer `"20"` par `"22"`.
- **Tests à prévoir** : Le pipeline CI validera lui-même le changement.
- **Risques** : Faible — les actions GitHub utilisent déjà Node 24 pour leurs propres exécutions.

### Étape 3 — Ajout de l'audit de sécurité npm dans le Dockerfile

- **Objectif** : Ajouter les deux commandes `npm audit` après `npm ci` dans le Dockerfile.
- **Fichiers** : `Dockerfile` (après la ligne 7)
- **Détails** : Insérer les deux lignes entre `RUN npm ci` et `COPY frontend ./`.
  ```dockerfile
  RUN npm audit fix --production --omit=dev || echo "audit-fix: continuing"
  RUN npm audit --omit=dev --audit-level=high || exit 1
  ```
  **Ordre important** : ces commandes doivent être exécutées avant `COPY frontend ./` pour bénéficier du cache Docker et ne pas copier le code inutilement si le build échoue.
- **Tests à prévoir** : `docker build` local. Vérifier que le build passe ou échoue avec un message clair si des vulnérabilités high+ persistent.
- **Risques** : Si `npm audit fix --production` modifie une dépendance transitive de façon incompatible, le build Next.js pourrait échouer à l'étape `npm run build`. C'est détecté avant la copie du code.

### Étape 4 — Mise à jour du README

- **Objectif** : Aligner la mention de version Node dans le README.
- **Fichiers** : `README.md` ligne 35
- **Détails** : `Node.js 20+ (22 recommandé)` → `Node.js 22+`
- **Tests à prévoir** : Aucun (documentation).
- **Risques** : Aucun.

## 7. Tests et vérifications attendus

```bash
# 1. Vérifier que l'image Docker se construit
cd "C:\Users\domin\Documents\Python Scripts\CourseScope"
docker build -t coursescope:test .

# 2. Vérifier que la CI passerait (impossible en local sans push, mais `npm run build` dans l'image couvre le même périmètre)
```

**Note** : Les tests backend et frontend existants (`pytest`, `npm test`) ne sont pas impactés — aucun code applicatif n'est modifié.

## 8. Critères d'acceptation

- [ ] `docker build` réussit sans erreur avec l'image `node:22-bookworm-slim`.
- [ ] Le warning `EBADENGINE` pour `camera-controls` disparaît du log de build.
- [ ] Le build échoue si une vulnérabilité npm **high** ou **critical** persiste après `audit fix --production` (vérifiable en reproduisant le scénario).
- [ ] La CI utilise Node 22 (`node-version: "22"` dans `ci_cd.yml`).
- [ ] Le README indique « Node.js 22+ » (plus de référence à Node 20).

## 9. Risques et garde-fous

| Risque | Garde-fou |
|---|---|
| `npm audit fix --production` casse une dépendance transitive | Le build Next.js échouerait à `npm run build` → détecté avant publication. Le `|| echo` évite un faux positif si `audit fix` échoue pour une raison non bloquante. |
| Node 22 introduit un changement cassant pour une dépendance | Next.js 16.1.5 est officiellement compatible Node 22. Three.js, React 19.2.3 le sont aussi. |
| Image Docker plus volumineuse | `node:22-bookworm-slim` a une taille comparable à `node:20-bookworm-slim` (~quelques MB d'écart). |

## 10. Décisions prises par agent-brainstorm

| Décision | Justification |
|---|---|
| Node 22, pas Node 24 | Node 24 n'est pas LTS. Le projet n'a pas besoin d'expérimenter avec une version non stable. La compatibilité de `camera-controls` est satisfaite dès Node >=22. |
| Blocage du build sur vulnérabilité **high+** uniquement | Les vulnérabilités moderate et low ne justifient pas un blocage du build — elles sont moins critiques et souvent dans des dépendances transitives non exploitables. |
| `audit fix --production` avant l'audit | Corrige automatiquement les vulnérabilités qui le peuvent, réduisant le bruit et ne bloquant que ce qui n'a pas de correctif disponible. |
| Commandes d'audit placées avant `COPY frontend ./` | Optimisation de cache Docker : si l'audit échoue, le build s'arrête avant la copie du code source (plus rapide, et évite de copier inutilement). |

## 11. Points à ne pas faire

- Ne pas modifier `frontend/package.json` (ni `overrides`, ni `resolutions`) — on laisse `npm audit fix` gérer les correctifs safe.
- Ne pas modifier les dépendances Python / `requirements.txt`.
- Ne pas modifier le code applicatif (`backend/`, `frontend/src/`, `tests/`).
- Ne pas ajouter `--force` à `npm audit fix` — casserait les dépendances.
- Ne pas retirer le `|| echo` de la ligne `audit fix` — cette commande peut échouer sans être bloquante (audit fix laisse parfois des CVE irrésolubles), le blocage doit venir de la ligne suivante.
