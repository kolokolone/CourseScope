# Workflow Agentique — CourseScope

> **Type** : Guide · **Cible** : Utilisateurs et agents IA
> **Dernière mise à jour** : 2026-06-30

Système de modification du code en deux étapes via des agents spécialisés.
Un agent analyse et planifie (read-only), l'autre implémente.

---

## Vue d'ensemble

```
┌──────────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
│  agents/                 │────▶│  agent-brainstorm.md     │────▶│  agent-brainstorm/        │
│  modifications.txt       │     │  (analyse + planifie)    │     │  modifications.md         │
│  (l'utilisateur écrit)   │     └──────────────────────────┘     └──────────┬───────────────┘
└──────────────────────────┘                                                 │
                                                                             ▼
                                                                   ┌──────────────────────────┐
                                                                   │  agent-dev.md            │
                                                                   │  (implémente)            │
                                                                   └──────────┬───────────────┘
                                                                              │
                                                                              ▼
                                                                   ┌──────────────────────────┐
                                                                   │  Code modifié            │
                                                                   │  + tests verts           │
                                                                   └──────────────────────────┘
```

---

## Fichiers

| Fichier | Rôle | Qui l'écrit |
|---|---|---|
| `agents/modifications.txt` | Demandes de changement en langage naturel | **L'utilisateur** |
| `agents/agent-brainstorm.md` | Prompt de l'agent analyste (read-only) | Fourni (ne pas modifier) |
| `agents/agent-brainstorm/modifications.md` | Plan d'implémentation détaillé | Agent Brainstorm |
| `agents/agent-dev.md` | Prompt de l'agent développeur | Fourni (ne pas modifier) |
| `agents/agent-review.md` | Prompt de l'agent auditeur (read-only par défaut) | Fourni (ne pas modifier) |
| `agents/AGENTS.md` | Règles globales pour tous les agents | Maintenu avec le projet |

---

## Comment l'utiliser

### Étape 1 — Écris tes modifications

Ouvre `agents/modifications.txt` et décris ce que tu veux changer, en langage naturel.
Tu peux faire des listes, écrire en prose, mélanger les deux. Sois précis mais pas technique.

Exemple :
```
## Dans "/progress" :
je veux implémenter deux fonctions :
- un Calendrier qui sera positionné sous le graphique "Volume hebdo"
- un graphique de charge sous le graphique "Charge (TRIMP) par semaine"

## Sur la page principale "/" :
- réduire la barre latérale de 15% de largeur
- ajouter la version à côté du titre "CourseScope"
```

### Étape 2 — Lance l'agent Brainstorm

1. Ouvre OpenCode
2. Donne le prompt `agents/agent-brainstorm.md` comme instructions
3. L'agent va :
   - Lire `agents/AGENTS.md` et la documentation du projet
   - Lire `agents/modifications.txt`
   - Analyser les fichiers concernés
   - Générer `agents/agent-brainstorm/modifications.md`

**Important** : l'agent Brainstorm ne modifie JAMAIS le code. Il lit et planifie uniquement.

### Étape 3 — Vérifie le plan

Ouvre `agents/agent-brainstorm/modifications.md` et vérifie que :
- Toutes tes demandes sont couvertes
- Les étapes sont logiques et dans le bon ordre
- Rien d'important n'a été oublié

Si quelque chose ne va pas, modifie `agents/modifications.txt` et relance l'étape 2.

### Étape 4 — Lance l'agent Dev

1. Ouvre une NOUVELLE session (ne pas mélanger avec Brainstorm)
2. Donne le prompt `agents/agent-dev.md` comme instructions
3. L'agent va :
   - Lire `agents/AGENTS.md` et la documentation du projet
   - Lire `agents/agent-brainstorm/modifications.md`
   - Lire tous les fichiers concernés
   - Implémenter chaque étape du plan
   - Vérifier que les tests passent et que le lint est propre

### Étape 5 — Audit (optionnel)

Lance `agents/agent-review.md` pour auditer le résultat.
L'agent review inspecte le frontend, le backend, les tests, la sécurité, la performance et la cohérence UI.
Par défaut, il travaille en lecture seule.

### Étape 6 — Commit

Une fois l'implémentation terminée et vérifiée :
```bash
git add -A
git commit -m "feat: description des changements"
git push
```

---

## Détail des agents

### Agent Brainstorm (`agents/agent-brainstorm.md`)

| Propriété | Valeur |
|---|---|
| Rôle | Architecte / Analyste |
| Peut modifier le code | ❌ Non (read-only) |
| Peut lire le code | ✅ Oui |
| Output | `agents/agent-brainstorm/modifications.md` uniquement |

**Ce qu'il fait :**
1. Lit `agents/AGENTS.md` et la documentation du projet
2. Lit `agents/modifications.txt` — le langage naturel de l'utilisateur
3. Analyse les fichiers qui seraient impactés par les changements
4. Produit un plan structuré avec :
   - Résumé en français
   - Liste des fichiers concernés
   - Étapes d'implémentation détaillées
   - Tests à créer ou modifier
   - Points d'attention et risques
   - Checklist de vérification post-implémentation

**Ce qu'il NE fait PAS :**
- Modifier du code
- Éditer des fichiers (sauf `agent-brainstorm/modifications.md`)
- Exécuter des commandes mutatives
- Deviner en cas d'ambiguïté (il la signale explicitement)

### Agent Dev (`agents/agent-dev.md`)

| Propriété | Valeur |
|---|---|
| Rôle | Développeur |
| Peut modifier le code | ✅ Oui |
| Peut lire le code | ✅ Oui |
| Peut exécuter des commandes | ✅ Oui (pytest, compileall, npm test, npm run build) |
| Output | Code modifié + tests verts |

**Ce qu'il fait :**
1. Lit `agents/AGENTS.md` et la documentation du projet
2. Lit `agents/agent-brainstorm/modifications.md` — le plan d'implémentation
3. Lit chaque fichier avant de le modifier
4. Implémente étape par étape
5. Vérification finale : tests backend + build frontend

**Règles strictes :**
- Ne pas casser la compatibilité API (`/xxx` et `/api/xxx`)
- Ne pas supprimer de fonctionnalité existante
- Respecter les conventions du code existant
- Pas de refactor global non demandé
- Jamais de `@ts-ignore`, `as any`, suppression de tests

### Agent Review (`agents/agent-review.md`)

| Propriété | Valeur |
|---|---|
| Rôle | Auditeur |
| Peut modifier le code | ❌ Non par défaut (sauf autorisation explicite) |
| Peut lire le code | ✅ Oui |
| Output | Rapport d'audit |

Inspecte : frontend, backend, tests, sécurité, performance, cohérence UI, dette technique.

---

## Format de `agent-brainstorm/modifications.md`

Le plan généré par Brainstorm suit cette structure :

```markdown
# Modifications Brainstorm — {YYYY-MM-DD}

## Résumé
(résumé 2-4 phrases en français)

## Demande originale
(copie du contenu de modifications.txt)

## Fichiers concernés
| Fichier | Rôle dans les modifications |

## Étapes d'implémentation
### Étape 1 — Titre
- Fichier(s)
- Description
- Changements précis
- Pattern à suivre
- Tests
- Risques

## Ordre d'exécution recommandé

## Points d'attention

## Checklist de vérification post-implémentation
```

---

## Journaux de session

Chaque session agent produit un journal dans son dossier de travail :

```text
agents/agent-brainstorm/YYMMDD.HHMM.agent-brainstorm.md
agents/agent-dev/YYMMDD.HHMM.agent-dev.md
agents/agent-review/YYMMDD.HHMM.agent-review.md
```

Format du nom : `YYMMDD.HHMM.nom-agent.md` (Windows-safe, sans deux-points).

Ne pas confondre le journal de session avec `agents/agent-brainstorm/modifications.md` :
- Le journal raconte ce qui a été fait
- `modifications.md` sert de cahier des charges pour agent-dev

---

## Bonnes pratiques

1. **Une demande à la fois** — ne mélange pas 10 changements dans le même `modifications.txt`
2. **Relis le plan Brainstorm** avant de le donner au Dev — c'est ton dernier point de contrôle
3. **Session propre pour le Dev** — ne réutilise pas la session Brainstorm
4. **Si le Dev échoue** — vérifie le plan Brainstorm, affine `modifications.txt`, recommence
5. **Commit après chaque cycle** — un commit par `modifications.txt` traité
6. **Lance l'audit régulièrement** — agent-review pour détecter la dette technique tôt
