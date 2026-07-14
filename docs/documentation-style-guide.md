# Guide de rédaction documentaire — CourseScope

Ce document définit comment créer, structurer et maintenir la documentation technique du projet CourseScope.

## Objectif

La documentation doit permettre à un nouveau développeur (ou à un agent IA) de :
1. Comprendre l'architecture du projet en moins de 10 minutes
2. Trouver l'information technique précise dont il a besoin
3. Contribuer sans casser les conventions existantes

## Types de documents

| Type | Emplacement | Public | Exemple |
|---|---|---|---|
| **Spécification** | `docs/` | Développeurs, agents | `progression.md`, `indexation.md` |
| **Référence technique** | `docs/` | Développeurs | `metrics_catalog.md`, `pace_vs_grade.md` |
| **Guide normatif** | `docs/` | Développeurs, agents | `style-frontend-ui.md`, `design.md` |
| **Procédure** | `docs/` | Opérateurs, agents | `documentation_update_runbook.md` |
| **Référence de domaine** | `docs/` | Développeurs, utilisateurs | `race-planning.md` |
| **Règles agent** | `agents/` | Agents IA | `AGENTS.md`, `agent-brainstorm.md` |
| **Meta-documentation** | `docs/` | Mainteneurs | Ce fichier |

## Structure d'un document

### En-tête obligatoire

Chaque document technique commence par :

```markdown
# Titre du document

## Objectif

Décrire en 2-3 phrases ce que ce document explique et à qui il s'adresse.

## Périmètre

Lister ce qui est couvert et ce qui ne l'est pas.
```

### Sections recommandées

Adapter selon le type de document :

- **Spécification** : Contexte → État actuel → Cible → Contrats → Implémentation → Tests
- **Référence** : Source des données → Algorithme → Format de sortie → Contrat API
- **Guide** : Principe → Règle → Exemple → Anti-pattern → Vérification

## Règles de rédaction

### Ton
- Direct, factuel, technique
- Français ou anglais selon le document, mais **une seule langue par document**
- Pas de superlatifs vagues
- Pas d'excuses (« c'est encore en dev »)

### Format
- Blocs de code pour les exemples
- Tableaux pour les données structurées (endpoints, champs, paramètres)
- Listes à puces pour les règles et contraintes
- Chemins de fichiers en backticks : `backend/api/routes/analysis.py`
- Commandes en blocs shell

### Nommage des fichiers
- `kebab-case.md` pour les noms de fichiers
- Préfixe cohérent : `agent-*` pour les docs agent, le reste sans préfixe
- Éviter les dates dans les noms de fichiers (sauf journaux de session)
- Éviter les noms trop génériques (`notes.md`, `todo.md`)

## Définition des termes

Utiliser un vocabulaire cohérent dans toute la documentation :

| Terme | Définition |
|---|---|
| **Activité** | Une activité réelle enregistrée, identifiée par `activity_id` |
| **Trace** | Un parcours GPX/FIT théorique, identifié par `trace_id` |
| **Analyse réelle** | Analyse d'une activité déjà effectuée |
| **Analyse théorique** | Estimation de temps/allure sur un parcours futur |
| **Série** | Une colonne de données temporelles (pace, HR, elevation...) |
| **Indexation** | Calcul et stockage des métriques agrégées pour la progression |
| **Fast** | Indexation rapide : synchronisation inventaire FS ↔ DB |
| **Slow** | Indexation complète : recalcul des métriques analytiques |
| **GAP** | Grade Adjusted Pace : allure corrigée de la pente |
| **VAM** | Vitesse Ascensionnelle Moyenne (m/h) |
| **TRIMP** | Training Impulse : charge d'entraînement |
| **EF** | Efficacité Aérobie : speed / HR |
| **Découplage** | Dérive cardiaque : écart FC entre 1ère et 2ème moitié |
| **Agent** | Programme IA spécialisé (Brainstorm, Dev, Review) |
| **Workflow** | Processus séquentiel Brainstorm → Dev → Review |

## Mise à jour

Quand modifier la documentation :

| Changement | Docs à mettre à jour |
|---|---|
| Nouvel endpoint ou champ API | `metrics_catalog.md` + `CHANGELOG.md` |
| Nouvelle page frontend | `style-frontend-ui.md` (si nouveau pattern) |
| Changement d'algorithme | Document technique correspondant (`pace_vs_grade.md`, `climbs.md`, etc.) |
| Changement de commande ou port | `README.md` |
| Nouvelle règle agent | `agents/AGENTS.md` |
| Changement du domaine trace | `race-planning.md` |
| Refacto majeur | document de référence du domaine concerné |

Suivre la procédure détaillée dans `documentation_update_runbook.md`.

## Vérification

Avant de publier un document :

- [ ] Le titre est clair et descriptif
- [ ] L'objectif est énoncé dans les 3 premières lignes
- [ ] Les chemins de fichiers sont corrects (vérifier qu'ils existent)
- [ ] Les liens internes pointent vers des fichiers existants
- [ ] Les commandes peuvent être copiées-collées
- [ ] Les exemples de code sont syntaxiquement corrects
- [ ] Aucune information obsolète n'est conservée « pour mémoire »
- [ ] Le document utilise le vocabulaire défini ci-dessus
- [ ] Le format est cohérent avec les documents similaires

## Anti-patterns

- ❌ Document qui duplique un autre document
- ❌ Document « fourre-tout » sans périmètre clair
- ❌ Section vide ou placeholder (« TODO: à compléter »)
- ❌ Référence vers un fichier supprimé
- ❌ Mélange français/anglais dans le même fichier
- ❌ Documentation générique non reliée au code réel
- ❌ Historique de modifications inline (utiliser `CHANGELOG.md`)
