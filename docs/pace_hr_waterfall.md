# Pace-HR Waterfall 3D

> **Type** : Spécification métrique · **Page** : `/progress` · **Endpoint** : `GET /progress/pace-hr-waterfall`
> **Dernière mise à jour** : v1.2.16

## Objectif

Le Pace-HR Waterfall 3D compare, activité après activité, la fréquence cardiaque observée pour une allure donnée. Les courbes sont ordonnées de la plus ancienne à la plus récente. À allure équivalente, une fréquence cardiaque plus basse peut indiquer une amélioration de l'efficacité aérobie.

La métrique est calculée lors de l'indexation lente et persistée dans `progress_pace_hr_bins`. Le rendu 3D ne relit pas les FIT/GPX et ne recalcule aucune statistique.

## Sources

Le pipeline utilise les colonnes du DataFrame canonique de l'activité :

| Colonne | Unité | Rôle |
|---|---:|---|
| `delta_time_s` | s | Fenêtre d'allure et pondération des bins |
| `delta_distance_m` | m | Calcul de l'allure glissante et temps initial en mouvement |
| `speed_m_s` | m/s | Disponible dans la source, mais non utilisée par ce pipeline |
| `heart_rate` | bpm | Fréquence cardiaque brute |

## Pipeline de préparation

Le prétraitement est implémenté dans `backend/core/pace_hr.py`. Il est volontairement continu et minimal : il n'utilise pas le masque de mouvement partagé, ne segmente pas les pauses ou les trous d'enregistrement et n'exclut pas les transitions d'allure.

### 1. Normalisation arithmétique minimale

Les temps et distances non finis ou négatifs sont remplacés par zéro afin de garder les sommes définies. Aucun seuil adaptatif de trou temporel n'est appliqué. Un intervalle long reste donc dans la fenêtre et une distance nulle n'entraîne pas de coupure de série.

### 2. Allure glissante

L'allure est recalculée sur une fenêtre continue de `30 s` :

```text
pace_s_per_km = temps_cumulé_fenêtre / distance_cumulée_fenêtre_km
```

Une fenêtre incomplète ou sans distance ne produit pas de valeur. Une pause ou un trou peut influencer la valeur de la fenêtre, mais ne redémarre pas le calcul.

### 3. Nettoyage de la fréquence cardiaque

La FC est limitée aux valeurs strictement comprises entre `40` et `240 bpm`, puis le pipeline applique :

1. un filtre de Hampel centré sur `11 s` ;
2. un seuil de `3 × 1,4826 × MAD`, avec un plancher de `8 bpm` ;
3. une médiane centrée finale sur `5 s`, avec au moins trois observations valides.

Il n'existe plus de contrôle de variation en bpm/s. Un point rejeté par Hampel ou hors bornes reste absent et n'est pas interpolé.

### 4. Échauffement initial

Les `600` premières secondes avec `delta_distance_m > 0` sont exclues. Sans masque de mouvement lissé, une distance positive est la définition minimale du temps en mouvement pour ce compteur.

### 5. Éligibilité finale

Un échantillon contribue aux bins lorsque :

```text
delta_time_s > 0
AND échauffement terminé
AND allure glissante finie et comprise entre 0 et 1800 s/km
AND FC nettoyée finie et issue d'une valeur brute entre 40 et 240 bpm
```

Il n'existe aucune condition liée au masque de mouvement, à une durée maximale d'intervalle ou à une transition d'allure.

## Indexation multi-résolution

Chaque activité est agrégée directement depuis les mêmes échantillons nettoyés dans quatre index natifs :

- `5 s/km` ;
- `10 s/km` ;
- `20 s/km` ;
- `30 s/km`.

Pour chaque résolution et chaque bin :

- `time_s_bin` est la somme des `delta_time_s` valides ;
- `hr_mean_w_bpm` est la moyenne FC pondérée par le temps ;
- `hr_q50_w_bpm` est la médiane FC pondérée par le temps ;
- le bin est conservé uniquement s'il contient au moins `60 s`.

Chaque résolution repart des échantillons nettoyés. Une résolution large n'est jamais calculée par moyenne de médianes provenant d'une résolution plus fine.

## Persistance et migration

La clé logique de `progress_pace_hr_bins` est :

```text
(activity_id, bin_step_s_per_km, pace_bin_s_per_km)
```

Le changement correspond à `METRICS_VERSION = 9`. Au premier démarrage, la migration reconstruit uniquement la table dérivée Pace-HR, puis une indexation lente recalcule les quatre résolutions des activités existantes.

`GET /progress/hr-at-pace` et `GET /progress/pace-at-hr` utilisent l'index natif `10 s/km`.

## Contrat du Waterfall

`GET /progress/pace-hr-waterfall` accepte exclusivement `bin_step_s_per_km=5|10|20|30`. Toute autre valeur retourne une erreur indiquant les résolutions natives disponibles.

Le chemin de lecture est strictement :

```text
activité
↓
bins définitifs de la résolution demandée
↓
réponse JSON
↓
affichage
```

Le service ne regroupe pas les bins, ne recalcule aucune moyenne et ne modifie pas leur résolution.

La réponse d'une activité contient uniquement son identifiant, sa date et ses points. Les filtres `session`, `terrain` et `endurance_only` ne font plus partie du contrat du Waterfall.

## Interface `/progress`

- résolution par défaut : `10 s/km` ;
- résolutions disponibles : `5`, `10`, `20`, `30 s/km` ;
- nombre d'activités par défaut : `60` ;
- limites disponibles : `10`, `30`, `60`, `120`.

Le style et le placement du composant 3D restent inchangés.

## Cas sans données

Une activité est absente lorsqu'elle ne contient pas assez de données après le nettoyage minimal, par exemple :

- absence de FC ;
- moins de dix minutes avec distance positive ;
- aucune fenêtre d'allure complète ;
- moins de `60 s` dans chaque bin de la résolution demandée.
