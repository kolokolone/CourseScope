# Guide universel de maintenance du README

> **Type** : Guide de référence · **Statut** : Référence (non normatif)
> **Note** : Ce document est un guide générique. Pour les règles spécifiques à CourseScope, voir [`docs/documentation-style-guide.md`](documentation-style-guide.md).

Ce document définit comment écrire, modifier et maintenir un `README.md` clair, utile et durable pour n'importe quel projet logiciel.

## Objectif

Le README est la **première chose qu'un humain lit**. Il doit répondre en moins de 30 secondes à :
1. C'est quoi ce projet ?
2. Pourquoi j'en ai besoin ?
3. Comment je l'installe ou je le lance ?

Tout ce qui relève de l'architecture détaillée, de la sécurité, des choix techniques profonds ou de l'historique du projet doit être renvoyé vers `docs/`.

## Structure recommandée

1. **Header** — titre, baseline en une phrase, badges utiles, liens vers la documentation
2. **Pourquoi ?** — problème résolu, cas d'usage principal, valeur concrète
3. **Fonctionnalités principales** — tableau synthétique avec statut visuel si utile : ✅ disponible, ⚠️ partiel, ❌ non pris en charge
4. **Démarrage rapide** — commandes minimales, résultat visible immédiatement
5. **Installation** — méthode recommandée d'abord, alternatives ensuite
6. **Configuration** — variables d'environnement, fichiers requis, paramètres critiques
7. **Utilisation** — interface, ligne de commande, API ou workflow selon le projet
8. **Fonctionnement** — pipeline général, règles métier critiques, comportements importants
9. **Développement** — commandes utiles pour tester, formater, lancer en mode dev
10. **Déploiement** — Docker, serveur, cloud ou toute autre méthode pertinente
11. **Sécurité** — points essentiels, sans détail excessif, avec lien vers `docs/security.md` si nécessaire
12. **Limites connues** — ce que le projet ne fait pas ou ne garantit pas
13. **Ressources complémentaires** — liens vers `docs/`, exemples, captures, schémas
14. **Footer** — licence, stack principale, statut du projet

Cette structure est un cadre. Elle doit être adaptée au type de projet : application web, CLI, bibliothèque, API, outil local, service Docker, plugin, script d'automatisation, etc.

## Règles d'écriture

### Ton

- Direct, factuel, non marketing.
- Pas de superlatifs vagues : éviter « incroyable », « révolutionnaire », « ultra-puissant ».
- Pas d'excuses inutiles : éviter « c'est encore en dev », « désolé si ce n'est pas parfait ».
- Préférer un français concis et technique à un style littéraire.
- Dire clairement les limites au lieu de les masquer.

### Format

- Un bloc de code par exemple.
- Des tableaux pour les données structurées : fonctionnalités, configuration, compatibilité, commandes.
- Des listes à puces pour les règles, contraintes et prérequis.
- Des chemins de fichiers en backticks : `config/.env`, `docs/architecture.md`.
- Des commandes en blocs shell.
- Des endpoints API en blocs HTTP si le projet expose une API.
- Éviter les longues notes décoratives ou les callouts excessifs.

### Longueur

- Chaque section doit tenir dans une capture d'écran sans scroll important.
- Si une section dépasse 20 lignes, déplacer le détail dans `docs/` et garder un résumé dans le README.
- Le README doit rester lisible rapidement. À titre indicatif, viser environ 150 lignes effectives hors blocs de code.

## Ce qui DOIT être dans le README

- Une phrase claire qui explique le projet.
- Le problème résolu ou le cas d'usage principal.
- Les prérequis exacts : langage, runtime, gestionnaire de paquets, Docker, base de données, système compatible.
- La commande minimale pour installer ou lancer le projet.
- Le résultat attendu après lancement : URL locale, commande de test, sortie CLI, fichier généré, écran attendu.
- La configuration minimale : fichier `.env`, `.env.example`, `config.yaml`, paramètres obligatoires.
- Les commandes de développement importantes : installation, lint, tests, build.
- Les informations de déploiement si le projet est prévu pour être déployé.
- Les limites fonctionnelles importantes.
- Les liens vers les documents détaillés dans `docs/`.
- La licence ou l'absence de licence explicite.

## Ce qui NE DOIT PAS être dans le README

- Les secrets, tokens, mots de passe, clés API ou identifiants réels.
- Les explications internes trop longues sur le fonctionnement du code.
- Les détails complets d'architecture : les placer dans `docs/architecture.md`.
- Les détails complets de sécurité : les placer dans `docs/security.md`.
- Les historiques de bugs, journaux de correction ou notes d'audit.
- Le changelog complet : le placer dans `CHANGELOG.md` si nécessaire.
- Les instructions de contribution longues : les placer dans `CONTRIBUTING.md` si le projet en a besoin.
- Les justifications détaillées de chaque choix technique. Une phrase suffit si le choix est important.
- Les informations obsolètes conservées « pour mémoire ».
- Les sections vides ou génériques qui n'aident pas l'utilisateur.

## Informations critiques à maintenir à jour

Quand ces éléments changent, le README doit être mis à jour :

| Élément | Où dans le README | Impact si obsolète |
|---|---|---|
| Version du projet | Header, badge ou footer | Confusion sur les fonctionnalités disponibles |
| Prérequis | Installation | L'utilisateur part avec une mauvaise configuration |
| Commandes de lancement | Démarrage rapide / Installation | Le projet ne peut pas être lancé |
| URLs, ports ou endpoints | Démarrage rapide / Utilisation | L'utilisateur ne trouve pas l'application ou l'API |
| Variables de configuration | Configuration | Erreurs au démarrage ou comportement inattendu |
| Fonctionnalités disponibles | Fonctionnalités principales | Attentes fausses de l'utilisateur |
| Limites connues | Limites connues | Fausse confiance dans le projet |
| Commandes de test et build | Développement | Les contributeurs perdent du temps |
| Méthode de déploiement | Déploiement | Déploiement cassé ou non reproductible |
| Liens vers `docs/` | Ressources complémentaires | Documentation inaccessible ou incohérente |

## Convention de nommage

- `README.md` — version stable actuelle.
- `README_old.md` — ancienne version conservée temporairement pour référence.
- `README_vN.md` — version de travail lors d'une refonte importante.
- `docs/` — documentation longue : architecture, sécurité, déploiement, API, décisions techniques.

Lors d'une refonte complète, créer d'abord une nouvelle version, relire, tester les commandes, puis remplacer le `README.md` principal.

## Checklist avant publication

Avant de remplacer le README principal :

- [ ] Le projet est expliqué clairement en une phrase.
- [ ] La section « Pourquoi ? » répond au besoin en moins de 4 phrases.
- [ ] Les prérequis sont exacts.
- [ ] Les commandes peuvent être copiées-collées dans un terminal.
- [ ] Le démarrage rapide contient uniquement le minimum nécessaire.
- [ ] Les URLs, ports, chemins et noms de fichiers sont corrects.
- [ ] Le tableau de configuration correspond aux fichiers de configuration réels.
- [ ] Les commandes de test, lint et build correspondent au projet.
- [ ] Les liens vers `docs/` pointent vers des fichiers existants.
- [ ] Aucun secret, token ou identifiant réel n'est présent.
- [ ] Les limites importantes sont indiquées explicitement.
- [ ] Le README ne contient aucune référence à un autre projet.
- [ ] Le README reste court, lisible et orienté utilisateur.

## Modèle minimal de README

````markdown
# Nom du projet

Phrase courte qui explique ce que fait le projet et pour qui.

## Pourquoi ?

Décrire le problème résolu, le contexte d'utilisation et la valeur concrète.

## Fonctionnalités principales

| Fonctionnalité | Statut | Remarque |
|---|---:|---|
| Fonction A | ✅ | Disponible |
| Fonction B | ⚠️ | Partiel ou expérimental |
| Fonction C | ❌ | Non pris en charge |

## Démarrage rapide

```bash
commande-d-installation
commande-de-lancement
```

Résultat attendu : ouvrir `http://localhost:XXXX` ou vérifier la sortie de la commande.

## Configuration

Copier le fichier d'exemple puis renseigner les valeurs nécessaires.

```bash
cp .env.example .env
```

| Variable | Obligatoire | Description |
|---|---:|---|
| `EXAMPLE_VAR` | Oui | Rôle de la variable |

## Utilisation

Décrire le chemin principal d'utilisation en quelques étapes.

## Développement

```bash
commande-de-test
commande-de-lint
commande-de-build
```

## Déploiement

Résumer la méthode recommandée et renvoyer vers `docs/deployment.md` si nécessaire.

## Sécurité

Ne jamais commiter de secrets. Voir `docs/security.md` pour les détails.

## Limites connues

- Limite importante 1.
- Limite importante 2.

## Licence

Indiquer la licence ou préciser qu'aucune licence n'est définie.
````
