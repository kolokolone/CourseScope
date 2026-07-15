# Pace-HR Waterfall 3D

> **Type** : Spécification métrique · **Page** : `/progress` · **Endpoint** : `GET /progress/pace-hr-waterfall`
> **Dernière mise à jour** : v1.2.14

## Objectif

Le Pace-HR Waterfall 3D compare, activité après activité, la fréquence cardiaque observée pour une allure donnée. Les courbes sont ordonnées de la plus ancienne à la plus récente. À allure équivalente, une fréquence cardiaque plus basse peut indiquer une amélioration de l'efficacité aérobie.

La métrique est calculée lors de l'indexation lente et persistée dans `progress_pace_hr_bins`. Le rendu 3D ne relit pas les fichiers FIT/GPX.

## Sources

Le pipeline utilise les colonnes du DataFrame canonique de l'activité :

| Colonne | Unité | Rôle |
|---|---:|---|
| `delta_time_s` | s | Pondération temporelle et détection des trous |
| `delta_distance_m` | m | Calcul de l'allure glissante |
| `speed_m_s` | m/s | Détection des pauses via le masque de mouvement partagé |
| `heart_rate` | bpm | Fréquence cardiaque brute |

## Pipeline de préparation

Le prétraitement est implémenté dans `backend/core/pace_hr.py`. Il est appliqué avant la construction des bins par `backend/progress/indexer.py`.

### 1. Masque de mouvement partagé

Le calcul réutilise `compute_moving_mask()` :

- médiane glissante de vitesse sur trois points ;
- seuil de mouvement à `0,5 m/s` ;
- pause reconnue après au moins `5 s` sous le seuil ;
- premier point de reprise conservé hors du temps en mouvement selon le comportement historique du masque.

Le Waterfall utilise ainsi la même définition du mouvement que les autres métriques de progression.

### 2. Trous temporels

La cadence d'échantillonnage de référence est la médiane des `delta_time_s` strictement positifs. La limite admise est :

```text
max_gap_s = min(15 s, max(5 s, 3 × delta_time_median))
```

Un intervalle non fini, négatif, nul ou supérieur à cette limite est exclu. Une pause ou un trou coupe la série en segments indépendants : aucune fenêtre de lissage ne traverse la coupure.

### 3. Allure glissante

L'allure n'est plus l'allure instantanée du point. Elle est calculée sur une fenêtre de `30 s` :

```text
pace_s_per_km = temps_cumulé_fenêtre / distance_cumulée_fenêtre_km
```

Cette formulation évite la moyenne arithmétique d'allures et reste robuste aux variations de fréquence d'échantillonnage. Une fenêtre incomplète ne produit pas de valeur.

### 4. Nettoyage de la fréquence cardiaque

La FC est d'abord limitée aux valeurs strictement comprises entre `40` et `240 bpm`.

Le nettoyage applique ensuite, séparément dans chaque segment continu :

1. un filtre de Hampel centré sur `11 s` ;
2. un seuil de `3 × 1,4826 × MAD`, avec un plancher de `8 bpm` ;
3. le rejet des variations supérieures à `5 bpm/s` ;
4. une médiane centrée finale sur `5 s`, avec au moins trois observations valides.

Un point rejeté n'est pas interpolé et ne contribue à aucun bin.

### 5. Échauffement

Les `600` premières secondes de temps réellement en mouvement sont exclues. Le compteur ne progresse pas pendant une pause ou un trou temporel.

Une activité trop courte peut donc ne produire aucun bin Pace-HR.

### 6. Changements d'allure

L'allure glissante courante est comparée à celle observée environ `15 s` auparavant. Une transition est détectée si :

```text
abs(delta_pace) >= max(30 s/km, 8 % de l'allure précédente)
```

Comme l'allure glissante révèle la transition après son début, l'exclusion est étendue rétroactivement jusqu'au début de la fenêtre de comparaison. La transition complète et les `30 s` de mouvement suivant sa détection sont ainsi exclues. Cette exclusion évite d'associer la FC de la transition à une allure qui vient de changer.

## Masque final

Un échantillon contribue aux bins uniquement si toutes les conditions suivantes sont vraies :

```text
moving_mask
AND delta_time valide
AND delta_distance positive
AND échauffement terminé
AND hors transition d'allure
AND allure glissante finie et comprise entre 0 et 1800 s/km
AND FC nettoyée finie et comprise entre 40 et 240 bpm
```

## Agrégation par activité

Les échantillons valides sont rangés dans des bins d'allure de `10 s/km`.

Pour chaque bin :

- `time_s_bin` : somme des `delta_time_s` valides ;
- `hr_mean_w_bpm` : moyenne FC pondérée par le temps ;
- `hr_q50_w_bpm` : médiane FC pondérée par le temps ;
- temps minimal conservé : `60 s`.

`hr_q50_w_bpm` est utilisée en priorité par les endpoints de progression.

## Persistance et consommateurs

La table `progress_pace_hr_bins` alimente :

- `GET /progress/pace-hr-waterfall` ;
- `GET /progress/hr-at-pace` ;
- `GET /progress/pace-at-hr`.

Le schéma SQLite et les contrats JSON restent inchangés. Le nouveau pipeline correspond à `METRICS_VERSION = 8` et exige une indexation lente complète des activités existantes.

## Rendu

Le rendu reste géré par `frontend/src/components/charts/PaceHr3DChart.tsx` :

- axe X : activités ordonnées dans le temps ;
- axe Y : fréquence cardiaque en bpm ;
- axe Z : allure en s/km, affichée en min/km ;
- couleur : gris pour les activités anciennes, rouge pour les plus récentes.

Le style, le placement et le contrat du composant ne sont pas modifiés par le prétraitement.

## Cas sans données

Une activité est absente du Waterfall lorsqu'elle ne contient pas assez de données valides après filtrage, par exemple :

- absence de FC ;
- durée en mouvement inférieure à l'échauffement exclu ;
- trous temporels importants ;
- changements d'allure trop fréquents ;
- moins de `60 s` dans chaque bin final.
