# AGENTS.md — CourseScope

Ce fichier définit les règles communes pour les agents qui travaillent sur CourseScope. Il doit être lu avant les fichiers spécialisés dans `/agents/`.

## 1. Identité du projet

CourseScope est une application locale d’analyse d’activités sportives, principalement running, à partir de fichiers GPX/FIT et de données Garmin.

Le projet combine :

- un frontend Next.js / React / TypeScript ;
- une API FastAPI / Python ;
- une intégration Garmin ;
- des analyses réelles et théoriques : allure, pente, dénivelé, zones, splits, séries, best efforts, cartes, progression et comparaisons ;
- un stockage runtime local sous `data/`.

Repo GitHub :

```text
https://github.com/kolokolone/CourseScope
```

Repo local de référence :

```text
C:\Users\domin\Documents\Python Scripts\CourseScope
```

## 2. Hiérarchie des instructions

Ordre de priorité :

1. demande explicite de l’utilisateur ;
2. règles de sécurité, de non-destruction et de confidentialité ;
3. présent fichier `AGENTS.md` ;
4. fichier spécialisé de l’agent dans `/agents/` ;
5. documentation du repo dans `/docs` ;
6. conventions observées dans le code existant.

Si deux instructions se contredisent, appliquer la plus restrictive et signaler l’ambiguïté dans le rapport final.

## 3. Workflow agentique principal

Le workflow standard du projet est séquentiel. Ne pas le court-circuiter sans demande explicite.

```text
1. L’utilisateur écrit les modifications souhaitées dans :
   docs/modifications.txt

2. L’utilisateur lance :
   agents/agent-brainstorm.md

3. agent-brainstorm lit docs/modifications.txt, analyse le repo, puis écrit la spécification consolidée dans :
   agents/agent-brainstorm/modifications.md

4. L’utilisateur lance :
   agents/agent-dev.md

5. agent-dev lit obligatoirement :
   agents/agent-brainstorm/modifications.md

6. agent-dev implémente les modifications dans le dépôt, avec tests et vérifications pertinentes.

7. agent-review peut ensuite être lancé pour auditer le résultat.
```

Le fichier canonique de transmission entre `agent-brainstorm` et `agent-dev` est donc :

```text
agents/agent-brainstorm/modifications.md
```

Ne pas utiliser `agents/modifications.md` sauf instruction explicite. Ce chemin est trop ambigu et ne correspond pas au workflow principal.

## 4. Agents disponibles

### `agents/agent-brainstorm.md`

Agent de conception produit, UX, architecture et cadrage technique.

Il lit :

```text
docs/modifications.txt
```

Il produit :

```text
agents/agent-brainstorm/modifications.md
```

Il ne modifie pas le code applicatif. Son rôle est de transformer une demande brute en spécification claire, priorisée et exploitable par `agent-dev`.

### `agents/agent-dev.md`

Agent d’implémentation.

Il lit obligatoirement :

```text
agents/agent-brainstorm/modifications.md
```

Il modifie le code de manière ciblée, ajoute ou adapte les tests nécessaires, respecte l’architecture existante et vérifie le résultat avec les commandes pertinentes.

### `agents/agent-review.md`

Agent d’audit critique.

Par défaut, il travaille en lecture seule. Il inspecte le frontend, le backend, les tests, la sécurité, la performance, la cohérence UI et la dette technique. Il peut corriger uniquement si l’utilisateur l’autorise explicitement.

## 5. Règles globales non négociables

### 5.1 Lire avant d’agir

Avant toute proposition ou modification :

- lire les fichiers concernés ;
- vérifier les conventions existantes ;
- identifier les effets de bord possibles ;
- distinguer les faits constatés, les hypothèses et les inférences.

Ne jamais modifier un fichier sans avoir compris son rôle.

### 5.2 Changer le minimum nécessaire

Une modification doit être proportionnée à la demande.

Interdits par défaut :

- refactor global non demandé ;
- changement d’architecture sans justification ;
- modification de contrat API non compatible ;
- suppression de fonctionnalité existante ;
- changement massif de style UI hors demande explicite ;
- renommage de fichiers ou dossiers sans raison forte.

### 5.3 Préserver la compatibilité API

Les endpoints existants doivent rester compatibles.

Règle importante du repo : les routes peuvent exister en `/xxx` et en `/api/xxx`. Ne pas casser cette compatibilité.

Toute nouvelle métrique doit être :

- optionnelle ou rétrocompatible ;
- documentée si le changement est user-facing ou modifie un contrat ;
- couverte par des tests si elle est calculée côté backend.

### 5.4 Protéger les données locales et les secrets

Ne jamais exposer, logger, committer ou copier :

- tokens Garmin ;
- cookies ou credentials ;
- fichiers runtime personnels ;
- contenu de `data/integrations/garmin/` ;
- fichiers `.env`, secrets ou clés ;
- traces personnelles non explicitement demandées.

Avant toute modification liée aux imports, traces ou intégrations, vérifier les risques de fuite, d’écrasement ou de corruption de données.

### 5.5 Respecter l’UI existante

Le style frontend est gouverné par :

```text
docs/style-frontend-ui.md
```

Règles clés :

- utiliser le shell global `AppShell` ;
- ne pas recréer de header global dans les pages ;
- ne pas recréer de container racine local ;
- déclarer les titres, sous-titres et containers dans `page-metadata.tsx` ;
- modifier la navigation uniquement via `nav.ts` ;
- utiliser les tokens Tailwind existants (`bg-card`, `text-muted-foreground`, `border-input`, etc.) ;
- privilégier les composants existants (`Card`, `Button`, primitives UI du projet) ;
- vérifier mobile, focus clavier, contraste et états loading/error/empty.

### 5.6 Documentation

Le runbook documentaire est :

```text
docs/documentation_update_runbook.md
```

Ne pas modifier `docs/*.md` sauf si :

- l’utilisateur le demande explicitement ;
- le changement modifie un contrat, une métrique, une commande, une page majeure ou un comportement user-facing ;
- l’agent spécialisé indique que la documentation est nécessaire et que l’utilisateur a validé cette mise à jour.

Exception : `docs/modifications.txt` est le fichier d’entrée utilisateur du workflow. Les agents peuvent le lire. Ils ne doivent pas l’écraser sauf demande explicite.

## 6. Commandes utiles

### Démarrage local

Windows :

```bash
./run_win.bat
```

Linux/macOS :

```bash
./run_linux.sh --dev
```

URLs de développement :

```text
Frontend: http://localhost:3000
API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
```

### Vérifications backend

```bash
python -m compileall backend
python -m pytest tests/pytest/
python -m pytest tests/unit/
python -m pytest -q
```

### Vérifications frontend

```bash
cd frontend
npm test
npm run build
```

Lancer uniquement les commandes pertinentes au changement si le scope est limité. Si une commande échoue, noter clairement :

- la commande lancée ;
- l’erreur observée ;
- si l’erreur semble liée au changement ou préexistante ;
- la correction proposée.

## 7. Fichiers de travail et journaux

Chaque agent possède un dossier de travail dédié :

```text
agents/agent-brainstorm/
agents/agent-dev/
agents/agent-review/
```

Le fichier de transmission principal est :

```text
agents/agent-brainstorm/modifications.md
```

Les journaux de session doivent utiliser un nom Windows-safe, sans deux-points `:`.

Format recommandé :

```text
YYMMDD.HHMM.nom-agent.md
```

Exemples :

```text
260622.1410.agent-brainstorm.md
260622.1415.agent-dev.md
260622.1420.agent-review.md
```

Emplacement recommandé des journaux :

```text
agents/agent-brainstorm/260622.1410.agent-brainstorm.md
agents/agent-dev/260622.1415.agent-dev.md
agents/agent-review/260622.1420.agent-review.md
```

Ne pas mélanger le journal de session avec `agents/agent-brainstorm/modifications.md`. Le premier raconte ce qui a été fait ; le second sert de cahier des charges pour `agent-dev`.

## 8. Format de réponse recommandé

Pour toute session importante, répondre avec :

1. résumé de ce qui a été fait ;
2. fichiers lus ;
3. fichiers modifiés, le cas échéant ;
4. commandes lancées ;
5. résultat des vérifications ;
6. risques restants ;
7. prochaine action recommandée.

## 9. Critères généraux de qualité

Une sortie est acceptable si elle est :

- spécifique au code existant ;
- vérifiable ;
- structurée ;
- proportionnée ;
- compatible avec les conventions du projet ;
- explicite sur les incertitudes ;
- directement exploitable par l’agent suivant.

Une sortie est mauvaise si elle est :

- générique ;
- non reliée aux fichiers réels ;
- trop large ;
- ambiguë ;
- non testable ;
- silencieuse sur les risques ;
- destructrice ou non rétrocompatible.
