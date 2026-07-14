---
version: alpha
name: CourseScope-design-analysis
description: >
  Application web locale d'analyse de courses à pied. Une UI produit sobre et technique,
  construite sur un fond bleu-gris clair (#f4f6f9), une typographie Space Grotesk 
  moderne, et une couleur primaire bleu marine profond (#1d3557) comme seul accent 
  chromatique. L'interface est pensée comme un dashboard technique : sidebar fixe, 
  cartes blanches ombrées légèrement, graphiques Recharts et cartes Leaflet au cœur 
  de l'expérience. Le design évoque un outil d'analyse sportive sérieux, ni ludique 
  ni austère — un compagnon technique pour coureurs exigeants.

colors:
  primary: "#1d3557"
  on-primary: "#f8fafc"
  primary-hover: "#27466b"
  background: "#f4f6f9"
  foreground: "#0f172a"
  card: "#ffffff"
  card-foreground: "#0f172a"
  muted: "#e8edf4"
  muted-foreground: "#475569"
  accent: "#dfe8f5"
  accent-foreground: "#0f172a"
  secondary: "#e2e8f0"
  secondary-foreground: "#0f172a"
  border: "#ced8e3"
  input: "#ced8e3"
  ring: "#7890b2"
  destructive: "#b42318"
  destructive-foreground: "#ffffff"
  semantic-success: "#16a34a"
  semantic-warning: "#ca8a04"
  semantic-info: "#2563eb"
  chart-running: "#1d3557"
  chart-theoretical: "#2563eb"
  chart-pace: "#2a9d8f"
  chart-heartrate: "#e63946"
  chart-elevation: "#16a34a"
  chart-power: "#f4a261"

typography:
  display:
    fontFamily: Space Grotesk
    fontSize: 2.5rem
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.025em
  heading-1:
    fontFamily: Space Grotesk
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: -0.02em
  heading-2:
    fontFamily: Space Grotesk
    fontSize: 1.25rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -0.01em
  card-title:
    fontFamily: Space Grotesk
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: -0.005em
  body:
    fontFamily: Space Grotesk
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  body-sm:
    fontFamily: Space Grotesk
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0
  caption:
    fontFamily: Space Grotesk
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: 0.01em
  mono:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0
  numeric:
    fontFamily: Space Grotesk
    fontSize: 0.875rem
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: 0
  button:
    fontFamily: Space Grotesk
    fontSize: 0.875rem
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: 0
  sidebar-brand:
    fontFamily: Space Grotesk
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -0.015em

rounded:
  none: 0
  sm: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px

spacing:
  xs: 0.25rem
  sm: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  xxl: 2rem
  section: 3rem

components:
  card-default:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-foreground}"
    rounded: "{rounded.lg}"
    border: 1px solid "{colors.border}"
    shadow: 0 1px 2px 0 rgba(0,0,0,0.05)
    padding: 0
  card-header-compact:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.lg}"
    padding: 0.75rem 1rem
  card-content-default:
    padding: 0 1rem 1rem 1rem
  card-title-default:
    typography: "{typography.card-title}"
    color: "{colors.card-foreground}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 0.5rem 1rem
    height: 2.5rem
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-outline:
    backgroundColor: transparent
    textColor: "{colors.foreground}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 0.5rem 1rem
    height: 2.5rem
    border: 1px solid "{colors.input}"
  button-outline-hover:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-foreground}"
  button-ghost:
    backgroundColor: transparent
    textColor: "{colors.foreground}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 0.5rem 1rem
    height: 2.5rem
  button-ghost-hover:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-foreground}"
  button-sm:
    height: 2.25rem
    padding: 0 0.75rem
    typography: "{typography.caption}"
  button-lg:
    height: 2.75rem
    padding: 0 2rem
    typography: "{typography.button}"
  button-icon:
    width: 2.5rem
    height: 2.5rem
    padding: 0
  input-default:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    border: 1px solid "{colors.input}"
    padding: 0.5rem 0.75rem
    height: 2.5rem
  input-focus:
    border: 1px solid "{colors.ring}"
    ring: 0 0 0 2px "{colors.ring}" at 25% opacity
  sidebar:
    backgroundColor: "{colors.card}"
    width: 260px
    borderRight: 1px solid "{colors.border}"
  sidebar-nav-item:
    backgroundColor: transparent
    textColor: "{colors.muted-foreground}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 0.5rem 0.75rem
  sidebar-nav-item-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.foreground}"
    borderLeft: 2px solid "{colors.primary}"
  sidebar-nav-item-hover:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-foreground}"
  top-header:
    backgroundColor: "{colors.background}"
    borderBottom: 1px solid "{colors.border}"
    padding: 1rem 1rem
  metric-kpi:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-foreground}"
    rounded: "{rounded.lg}"
    border: 1px solid "{colors.border}"
    shadow: 0 1px 2px 0 rgba(0,0,0,0.05)
    padding: 1rem
  metric-label:
    typography: "{typography.caption}"
    color: "{colors.muted-foreground}"
  metric-value:
    typography: "{typography.heading-1}"
    color: "{colors.foreground}"
  tab-default:
    backgroundColor: transparent
    textColor: "{colors.muted-foreground}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 0.5rem 1rem
    border: none
  tab-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.foreground}"
    borderBottom: 2px solid "{colors.primary}"
  badge-default:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-foreground}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: 0.125rem 0.625rem
  badge-success:
    backgroundColor: "#dcfce7"
    textColor: "#166534"
  badge-warning:
    backgroundColor: "#fef9c3"
    textColor: "#854d0e"
  badge-destructive:
    backgroundColor: "{colors.destructive}"
    textColor: "{colors.destructive-foreground}"
  file-dropzone:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.muted-foreground}"
    rounded: "{rounded.lg}"
    border: 2px dashed "{colors.border}"
    padding: 2rem
  file-dropzone-drag:
    backgroundColor: "{colors.accent}"
    border: 2px dashed "{colors.primary}"
  toast-default:
    backgroundColor: "{colors.foreground}"
    textColor: "{colors.card}"
    rounded: "{rounded.lg}"
    shadow: 0 10px 25px -5px rgba(0,0,0,0.15)
    padding: 1rem
  toast-destructive:
    backgroundColor: "{colors.destructive}"
    textColor: "{colors.destructive-foreground}"
  toast-success:
    backgroundColor: "{colors.semantic-success}"
    textColor: white
  chart-container:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-foreground}"
    rounded: "{rounded.lg}"
    border: 1px solid "{colors.border}"
    shadow: 0 1px 2px 0 rgba(0,0,0,0.05)
    padding: 1rem
  progress-bar:
    backgroundColor: "{colors.muted}"
    rounded: "{rounded.full}"
    height: 0.5rem
  progress-bar-fill:
    backgroundColor: "{colors.primary}"
    rounded: "{rounded.full}"
  page-container:
    maxWidth: 72rem
    padding-x: 1rem
    padding-y: 1.5rem
  page-container-wide:
    maxWidth: 88rem
    padding-x: 1rem
    padding-y: 1.5rem
  skeleton:
    backgroundColor: "{colors.muted}"
    rounded: "{rounded.md}"
---
document_type: design-system
status: actif
last_updated: 2026-06-30
---

> **Type** : Design system · **Statut** : Actif · **Cible** : Développeurs frontend et agents IA

## Overview

CourseScope est une application web d'analyse de courses à pied, fonctionnant en local. Son interface est un **dashboard technique sobre** — pensée comme un outil de travail quotidien pour coureurs exigeants, pas comme un site marketing.

Le design s'articule autour de :
- Un **fond bleu-gris clair** (`{colors.background}` #f4f6f9) qui apporte de la respiration sans être blanc clinique
- Une **couleur primaire bleu marine profond** (`{colors.primary}` #1d3557) utilisée uniquement pour les CTA principales et la navigation active — jamais décorative
- Des **cartes blanches** (`{colors.card}` #ffffff) avec ombre légère (`shadow-sm`) qui structurent l'information
- Une **typographie Space Grotesk** moderne, technique mais chaleureuse, avec JetBrains Mono pour les données chiffrées
- Une **sidebar fixe** de 260px comme colonne vertébrale de navigation
- Des **graphiques Recharts** et **cartes Leaflet** comme éléments centraux de l'expérience (pas de stock photos, pas d'illustrations décoratives)

**Caractéristiques clés :**
- **Dashboard-first** — l'interface est un outil, pas une vitrine. Pas de hero sections, pas de dégradés atmosphériques.
- **Light mode uniquement** — pas de dark mode. Le fond clair favorise la lisibilité des graphiques et des cartes.
- **Un seul accent chromatique** (`{colors.primary}`) — pas de palette de couleurs marketing. Les couleurs vives sont réservées aux visualisations de données (graphiques).
- **Espacement constant** — `space-y-4` entre cartes, `gap-4` en grille. Pas d'espacements fantaisistes.
- **Sidebar + Header + Content** — structure en trois zones immuable. Pas de variations de layout par page.

## Colors

### Surface & Background
- **Background** (`{colors.background}`) : Fond général de l'application. Un bleu-gris très clair (#f4f6f9) — ni blanc pur, ni gris froid.
- **Card** (`{colors.card}`) : Surface des cartes et de la sidebar. Blanc pur (#ffffff) pour un contraste net avec le fond.
- **Muted** (`{colors.muted}`) : Surface secondaire pour les dropzones, les états hover légers, les séparations subtiles. #e8edf4.
- **Secondary** (`{colors.secondary}`) : Fond des boutons secondaires. Très proche de muted, légèrement plus saturé (#e2e8f0).

### Brand & Accent
- **Primary** (`{colors.primary}`) : La signature visuelle de CourseScope. Bleu marine profond (#1d3557). Usage : CTA principale, indicateur d'onglet actif dans la sidebar, barres de progression, remplissage des graphiques "réel".
- **Primary Hover** (`{colors.primary-hover}`) : État hover des boutons primary. Légèrement éclairci (#27466b).
- **Accent** (`{colors.accent}`) : Fond d'état actif/hover dans la navigation et les onglets. Bleu très clair (#dfe8f5).

### Text
- **Foreground** (`{colors.foreground}`) : Texte principal, titres de cartes, valeurs KPI. Slate-900 (#0f172a) — presque noir mais pas #000.
- **Muted Foreground** (`{colors.muted-foreground}`) : Texte secondaire, sous-titres, labels de métriques. Slate-600 (#475569).
- **On-Primary** (`{colors.on-primary}`) : Texte sur fond primaire. Blanc cassé (#f8fafc).

### Semantic
- **Destructive** (`{colors.destructive}`) : Actions destructrices (supprimer, reset). Rouge foncé (#b42318).
- **Success** (`{colors.semantic-success}`) : Indicateurs positifs, badges de complétion. Vert (#16a34a).
- **Warning** (`{colors.semantic-warning}`) : Avertissements. Ambre (#ca8a04).
- **Info** (`{colors.semantic-info}`) : Information neutre. Bleu standard (#2563eb).

### Chart Colors (data visualization only)
Ces couleurs sont **exclusivement réservées aux graphiques** — jamais utilisées dans l'UI structurelle.
- **Running** (`{colors.chart-running}`) : Allure réelle, données GAP. #1d3557 (identique à primary pour cohérence).
- **Theoretical** (`{colors.chart-theoretical}`) : Prévisions, allure théorique. Bleu (#2563eb).
- **Pace** (`{colors.chart-pace}`) : Graphiques d'allure. Teal (#2a9d8f).
- **Heart Rate** (`{colors.chart-heartrate}`) : Fréquence cardiaque. Rouge (#e63946).
- **Elevation** (`{colors.chart-elevation}`) : Dénivelé, altitude. Vert (#16a34a).
- **Power** (`{colors.chart-power}`) : Puissance (watt). Orange (#f4a261).

### Color Usage Rules
1. **Toujours préférer les tokens** (`bg-card`, `text-muted-foreground`, `border-input`) aux couleurs hardcodées.
2. Les couleurs hardcodées sont **tolérées uniquement pour les graphiques** (Recharts, Leaflet).
3. Ne **jamais** utiliser les couleurs de graphiques dans l'UI structurelle (pas de badge teal, pas de bouton orange).
4. Le contraste texte secondaire (`{colors.muted-foreground}`) doit rester lisible — ne pas l'utiliser sur fond `{colors.muted}`.

## Typography

### Font Families
- **Space Grotesk** (variable, subsets latin) — Police principale pour tout le texte UI : titres, corps, labels, boutons, valeurs. C'est le seul choix typographique pour l'interface.
- **JetBrains Mono** (variable, subsets latin) — Police monospace réservée aux données techniques : timestamps, identifiants d'activité, code snippets, valeurs de précision.
- Fallback système implicite via `next/font/google` — ne pas spécifier manuellement.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `display` | 2.5rem | 600 | 1.15 | -0.025em | Page d'accueil uniquement (brand) |
| `heading-1` | 1.5rem (24px) | 600 | 1.25 | -0.02em | Titre de page dans le header |
| `heading-2` | 1.25rem (20px) | 600 | 1.3 | -0.01em | Titres de sections dans les pages |
| `card-title` | 1rem (16px) | 600 | 1.35 | -0.005em | Titres de cartes (CardTitle) |
| `body` | 0.875rem (14px) | 400 | 1.5 | 0 | Corps de texte, contenu de cartes |
| `body-sm` | 0.8125rem (13px) | 400 | 1.45 | 0 | Sous-texte dans les cartes |
| `caption` | 0.75rem (12px) | 400 | 1.35 | 0.01em | Labels de métriques, dates, footers |
| `mono` | 0.8125rem (13px) | 400 | 1.6 | 0 | Données techniques, IDs |
| `numeric` | 0.875rem (14px) | 600 | 1.5 | 0 | Valeurs chiffrées (KPI, stats) |
| `button` | 0.875rem (14px) | 500 | 1.2 | 0 | Labels de tous les boutons |
| `sidebar-brand` | 1.125rem (18px) | 600 | 1.3 | -0.015em | Nom de l'app dans la sidebar |

### Principles
- **Une seule famille pour toute l'UI** — Space Grotesk fait tout le travail structurel. Le mono n'intervient que pour les données.
- **Le tracking négatif est réservé aux titres** (heading-1, card-title, sidebar-brand). Le corps utilise un tracking neutre.
- **Les valeurs numériques sont en semibold + tabular-nums** pour un alignement parfait dans les grilles de KPIs.
- **Pas d'italique dans l'UI** — Space Grotesk n'a pas de vraie italique. Si nécessaire, utiliser le style normal avec une variation de couleur.

## Layout

### Shell Architecture

L'application utilise une grille CSS fixe en deux colonnes — c'est la seule structure de page autorisée :

```
┌──────────┬──────────────────────────────────────────┐
│          │  TopHeader (sticky)                       │
│ Sidebar  ├──────────────────────────────────────────┤
│ 260px    │                                          │
│          │  PageContainer (scrollable)               │
│          │    ┌──────────────────────────────────┐   │
│          │    │  Contenu métier (cards, charts)  │   │
│          │    │  max-w-6xl ou max-w-[88rem]      │   │
│          │    └──────────────────────────────────┘   │
│          │                                          │
└──────────┴──────────────────────────────────────────┘
```

**Règles immuables :**
- Le shell est défini dans `AppShell.tsx` — **unique source de vérité**.
- Sidebar : 260px fixes, scroll interne indépendant.
- Header : sticky en haut de la colonne contenu, avec titre + sous-titre + actions.
- Aucune page ne doit recréer un header, une sidebar, ou un container local.

### PageContainer

Deux variantes de largeur maximale :
- **`default`** : `max-w-6xl` (72rem) — pour les pages de liste, paramètres, accueil.
- **`wide`** : `max-w-[88rem]` — pour les pages d'analyse (activité/trace) avec graphiques denses.

Padding standard : `px-4 sm:px-6 lg:px-8` horizontal, `py-6` vertical.

### Spacing System

L'espacement suit un rythme constant basé sur Tailwind :
- **Entre cartes** : `space-y-4` (1rem / 16px)
- **Entre éléments d'une grille** : `gap-4` (1rem / 16px)
- **Entre sections** : `space-y-6` ou marge supplémentaire via composant parent
- **Padding intérieur des cartes (header)** : `py-3 px-4` (0.75rem / 12px vertical)
- **Padding intérieur des cartes (content)** : `px-4 pb-4`

### Grid Patterns

- Grilles responsives standard : `grid grid-cols-1 md:grid-cols-2 gap-4`
- Grilles de KPIs : `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4`
- Pour les pages wide (analyse) : `grid grid-cols-1 xl:grid-cols-2 gap-4`

### Rules of Composition

Chaque page doit :
1. Rendre uniquement le contenu métier (pas de chrome UI).
2. Commencer par un wrapper `space-y-4`.
3. Structurer les sections avec `Card` (CardHeader + CardContent).
4. Utiliser les grilles responsives standard.
5. **Ne jamais** dupliquer header / sidebar / container.

## Elevation & Depth

CourseScope utilise un système d'élévation subtil à 5 niveaux, sans ombres portées lourdes. L'approche est celle d'un outil technique : les surfaces se distinguent par leur fond, leur bordure, et une ombre légère — jamais par des effets "material" ou "glassmorphism".

| Level | Name | Shadow | Border | Use |
|---|---|---|---|---|
| 0 | Flat | Aucune | Aucune | Fond de page `{colors.background}`, contenu inline |
| 1 | Card | `0 1px 2px 0 rgba(0,0,0,0.05)` | 1px `{colors.border}` | Cartes, KPIs, conteneurs de graphiques, sidebar |
| 2 | Sticky | Aucune (backdrop blur) | 1px bottom `{colors.border}` | TopHeader uniquement |
| 3 | Raised | `0 4px 12px -2px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)` | 1px `{colors.border}` | Modales, dropdowns |
| 4 | Overlay | Aucune (fond semi-transparent) | Aucune | Drawer mobile (`bg-black/45`), backdrop de modale |

### Principes d'élévation
- **Jamais d'ombres colorées** — toutes les ombres sont en `rgba(0,0,0, ...)`. L'application n'a pas de "glow" coloré.
- **Pas d'ombres empilées** (contrairement à Vercel) — CourseScope garde une ombre unique par niveau pour la simplicité.
- **La bordure est plus importante que l'ombre** pour délimiter les surfaces. L'ombre est un complément subtil, pas le mécanisme principal.
- **Pas d'effet de flou d'arrière-plan** sauf sur le header sticky (`backdrop-blur`).

## Shapes

### Border Radius

| Token | Value | Tailwind | Use |
|---|---|---|---|
| `none` | 0 | `rounded-none` | Pas utilisé en pratique |
| `sm` | 0.25rem | `rounded-sm` | Petits éléments inline |
| `md` | 0.375rem | `rounded-md` | **Boutons**, inputs, onglets |
| `lg` | 0.5rem | `rounded-lg` | **Cartes**, containers, dropzones |
| `xl` | 0.75rem | `rounded-xl` | Modales, grands conteneurs |
| `full` | 9999px | `rounded-full` | Badges, avatars, barres de progression |

### Règles de forme
- **Les cartes sont toujours `rounded-lg`** — c'est le radius standard pour tous les contenants.
- **Les boutons sont toujours `rounded-md`** — plus serré pour un aspect fonctionnel.
- **Les badges utilisent `rounded-full`** — forme pilule pour distinguer du contenu.
- **Pas de `rounded-xl` ou `rounded-2xl` sur les cartes** — CourseScope est un outil, pas un site vitrine.

## Components

### Navigation

**`sidebar`** — Colonne de navigation fixe à gauche.
- Largeur : 260px, fond `{colors.card}`, bordure droite `{colors.border}`.
- Section brand en haut (nom "CourseScope" + sous-titre).
- Navigation principale (`main`) au centre, navigation secondaire (`footer`) en bas.
- Items : pleine largeur, icône Lucide à gauche, libellé à droite, `rounded-md`.

**`sidebar-nav-item`** — Item de navigation standard.
- Fond transparent, texte `{colors.muted-foreground}`.
- États :
  - **Hover** : fond `{colors.accent}`, texte `{colors.accent-foreground}`.
  - **Actif** : fond `{colors.accent}`, bordure gauche 2px `{colors.primary}`.
  - **Focus** : `focus-visible:ring-2 focus-visible:ring-ring`.
- Route dynamique : `/activities/[id]` active l'item parent `/activities`. `/traces/[id]` active `/traces`.

**`top-header`** — Barre supérieure sticky.
- Fond `{colors.background}` avec backdrop blur, bordure basse `{colors.border}`.
- Gauche : `h1` (titre de page) + sous-titre optionnel.
- Droite : date du jour (optionnelle) + actions de page (slot `HeaderActions`).
- Mobile : bouton menu hamburger (ouvre le drawer).

**Drawer mobile** — Navigation latérale sur mobile.
- Overlay `bg-black/45`, largeur `18rem` (max `88vw`).
- Fermeture : clic overlay, touche Escape, changement de route.

### Cards

**`card-default`** — Le conteneur universel pour tout contenu structuré.
- Fond `{colors.card}`, texte `{colors.card-foreground}`, `rounded-lg`, `border`, `shadow-sm`.
- Structure interne : `CardHeader` (optionnel) → `CardContent` → `CardFooter` (optionnel).

**`card-header-compact`** — Header de carte standard.
- Padding réduit : `py-3 px-4` (au lieu du `p-6` par défaut de shadcn/ui).
- Contient `CardTitle` + optionnellement `CardDescription`.

**`card-content-default`** — Contenu de carte.
- Padding : `px-4 pb-4` (le `pt-0` est géré par la relation header/content).

### Buttons

**`button-primary`** — CTA principale.
- Fond `{colors.primary}`, texte `{colors.on-primary}`, hauteur 2.5rem (h-10), padding 0.5rem 1rem.
- Hover : fond `{colors.primary-hover}`.
- Focus : `ring-2 ring-ring ring-offset-2`.
- Usage : action principale de la page (upload, sauvegarder, analyser).

**`button-outline`** — Action secondaire.
- Fond transparent, bordure `{colors.input}`, texte `{colors.foreground}`.
- Hover : fond `{colors.accent}`, texte `{colors.accent-foreground}`.
- Usage : actions secondaires (exporter, annuler, paramètres avancés).

**`button-ghost`** — Action tertiaire, sans bordure.
- Fond transparent, pas de bordure.
- Hover : fond `{colors.accent}`.
- Usage : navigation inline, actions mineures.

**`button-sm`** — Bouton compact.
- Hauteur 2.25rem (h-9), padding 0 0.75rem (px-3).
- Usage : actions dans le header, groupes de boutons.

### Inputs & Forms

**`input-default`** — Champ de saisie standard.
- Fond `{colors.background}`, bordure `{colors.input}`, hauteur 2.5rem, `rounded-md`.
- Focus : bordure `{colors.ring}` + ring.

### Data Display

**`metric-kpi`** — Carte de métrique individuelle (KPI).
- Fond `{colors.card}`, `rounded-lg`, `border`, `shadow-sm`.
- Contenu : label en caption + valeur en heading-1 + unité en caption.
- Grille standard : 2 à 4 colonnes selon breakpoint.

**`chart-container`** — Conteneur de graphique.
- Fond `{colors.card}`, `rounded-lg`, `border`, `shadow-sm`, padding 1rem.
- Contient un graphique Recharts avec titre et légende.

**`badge-default`** — Badge/pillule.
- Fond `{colors.accent}`, texte `{colors.accent-foreground}`, `rounded-full`.
- Variantes : `badge-success` (vert), `badge-warning` (ambre), `badge-destructive` (rouge).

**`progress-bar`** — Barre de progression.
- Fond `{colors.muted}`, `rounded-full`, hauteur 0.5rem.
- Fill : fond `{colors.primary}`, `rounded-full`.

### Feedback

**`toast-default`** — Notification toast.
- Fond `{colors.foreground}` (inversé), texte `{colors.card}`, `rounded-lg`.
- Variantes : `toast-success` (vert), `toast-destructive` (rouge).

**`file-dropzone`** — Zone de drop pour upload.
- Fond `{colors.muted}`, bordure 2px dashed `{colors.border}`, `rounded-lg`.
- État drag actif : fond `{colors.accent}`, bordure dashed `{colors.primary}`.

**`skeleton`** — État de chargement.
- Fond `{colors.muted}`, `rounded-md`, animation pulse.
- Usage : pendant le chargement initial des activités et des analyses.

## Signature Components

Ces patterns sont les marqueurs visuels distinctifs de CourseScope — ce qui rend l'application immédiatement reconnaissable.

### Sidebar with Active Indicator
La sidebar CourseScope n'est pas une simple liste de liens. Son identité visuelle repose sur :
- **L'indicateur actif gauche** : une barre verticale de 2px en `{colors.primary}` sur le bord gauche de l'item actif. C'est le marqueur le plus distinctif de la navigation.
- **Icônes Lucide** : chaque item a une icône à gauche, le libellé à droite. Les icônes sont en `{colors.muted-foreground}` par défaut, et passent en `{colors.foreground}` à l'état actif.
- **Section brand en haut** : séparée du reste par un `border-b`, avec le nom "CourseScope" en `text-lg font-semibold tracking-tight`.
- **Séparation main/footer** : la navigation principale est dans un bloc scrollable, la navigation secondaire (Paramètres) est épinglée en bas, séparée par un `border-t`.

### Compact Card Headers
Contrairement au shadcn/ui standard (`p-6` sur CardHeader), CourseScope utilise systématiquement `py-3 px-4` sur les headers de carte. Ce padding réduit est une signature visuelle — il dit "outil dense, pas page marketing".

### KPI Grid with tabular-nums
Les métriques clés (distance, temps, allure, D+) sont affichées dans une grille de cartes où chaque valeur utilise `font-semibold tabular-nums`. L'alignement parfait des chiffres dans la grille est un signal de qualité technique — les données sont traitées avec précision.

### File Dropzone
La zone d'upload GPX/FIT est un composant signature de la page d'accueil : fond `{colors.muted}`, bordure `dashed` de 2px en `{colors.border}`, icône d'upload au centre, texte d'instruction en `{colors.muted-foreground}`. L'état de drag actif passe le fond en `{colors.accent}` et la bordure en `{colors.primary}` — un feedback immédiat et satisfaisant.

### Chart-in-Card Pattern
Chaque graphique (Recharts) est encapsulé dans une `Card` avec `CardHeader` (titre + description) et `CardContent` (le graphique). Les graphiques ne flottent jamais librement sur le fond de page — le cadre blanc avec ombre légère fait partie de l'identité visuelle.

### Map with Trace Overlay
La carte Leaflet pour le tracé GPS est un composant signature. Le fond de carte par défaut est clair et épuré, le tracé est en `{colors.chart-running}` (bleu marine), et les marqueurs de pause/climb sont superposés. La carte est toujours dans une `Card` avec un header indiquant "Tracé GPS" ou "Parcours".

### Data-Density Philosophy
CourseScope est conçu pour afficher beaucoup d'informations sans submerger l'utilisateur. Les patterns qui permettent cette densité :
- **Sections conditionnelles** : Running Dynamics, Puissance avancée, etc. n'apparaissent que si les données sont disponibles — pas de placeholders vides.
- **Domaines séparés** : une activité réelle reste sous `/activities/{activity_id}` ; une trace et sa préparation restent sous `/traces/{trace_id}`.
- **Grilles responsives** : 4 KPIs en desktop large, 2 en tablette, 1 en mobile — l'information se réorganise sans se perdre.

## Page-Specific Patterns

### Page d'accueil (`/`)
- Conteneur `default`.
- Zone de drop pour upload GPX/FIT (composant `file-dropzone`).
- Liste des activités récentes en dessous.

### Activités (`/activities`)
- Conteneur `default`.
- Liste/tri des activités avec actions (sync Garmin, suppression).
- Actions header : boutons de sync et upload.

### Analyse d'activité (`/activities/[id]`)
- Conteneur `wide`.
- Analyse d'une activité réelle uniquement.
- La page bêta est devenue la page canonique ; `/activities-beta/[id]` reste un alias de compatibilité.
- Le hero reprend le conteneur de préparation de trace : carte `rounded-2xl`, bordure et ombre légères, fond analytique en dégradé discret `primary/background/emerald`, libellé de domaine avec icône, titre renommable et métadonnées.
- Le hero ne duplique pas la navigation globale avec un bouton « Retour aux activités ».
- Les KPI propres à l'activité restent inchangés et sont placés dans la grille du hero.
- « Analyse principale » affiche uniquement l'allure, la fréquence cardiaque et l'altitude, synchronisées par interpolation sur la distance plutôt que par index.
- L'API fournit l'axe X en kilomètres explicites ; le graphique affiche des graduations entières et dynamiques. L'allure bleue est à gauche, la fréquence cardiaque à droite avec une borne basse à `80 %` de la FC minimale observée.
- L'altitude utilise un axe masqué indépendant sur toute la hauteur et un dégradé vert ; la fréquence cardiaque ne possède aucun remplissage.
- Le lissage `15` est actif par défaut. Le survol du graphique sélectionne le point cartographique le plus proche par distance explicite.
- Les histogrammes « Temps par allure » et « Temps par % de pente » utilisent le calcul backend commun aux traces et précèdent « Allure vs Pente ».
- Un dernier split strictement inférieur à 500 m est masqué. La barre de zones renormalise les durées positives pour toujours occuper exactement sa largeur.

### Traces GPX (`/traces`, `/traces/[id]`)
- Conteneur `default` (liste), `wide` (analyse).
- Import partagé entre l'accueil et `/traces` via `TraceUpload`.
- Hero et KPI, sous-navigation sticky et cartes `AnalysisCard` partagées avec l'architecture d'`/activities-beta`.
- Grille responsive, carte et profil synchronisés, tableaux mobiles avec défilement horizontal.
- Paramètres persistés : objectif, date/départ, scénarios, pauses, stratégie, nutrition et matériel.
- Les trois graphiques reçoivent leurs séries du backend ; aucun calcul métier n'est dupliqué dans la page.

### Progression (`/progress`)
- Conteneur `default`.
- Graphiques multi-activités (tendances, best efforts, HR at pace, etc.).
- Filtres par période et type d'activité.
- Le calendrier annuel utilise toute la largeur disponible ; les cellules restent carrées et conservent leurs proportions.

### Objectifs (`/goals`)
- Conteneur `default`.
- Liste des courses/trails à venir.

### Paramètres (`/settings`)
- Conteneur `default`.
- Formulaires : VMA, FC max, préférences.
- Intégration Garmin : connexion, statut, reset.

## Do's and Don'ts

### Do
- Utiliser le shell `AppShell` comme seul wrapper de page — ne jamais le contourner.
- Déclarer les métadonnées de page dans `page-metadata.tsx` (titre, sous-titre, container, actions).
- Utiliser les tokens CSS (`bg-card`, `text-muted-foreground`, `border-input`) pour toute l'UI structurelle.
- Structurer le contenu des pages en `Card` avec `CardHeader` compact (`py-3 px-4`).
- Suivre le rythme d'espacement constant : `space-y-4` entre cartes, `gap-4` en grille.
- Utiliser `tabular-nums` pour toutes les valeurs numériques affichées en grille.
- Réserver `JetBrains Mono` aux données techniques (timestamps, IDs, valeurs de précision).
- Fournir des labels `aria-label` sur tous les boutons icon-only.
- Assurer un focus visible (`focus-visible:ring-2 focus-visible:ring-ring`) sur tous les éléments interactifs.
- Utiliser les icônes Lucide React exclusivement — ne pas introduire d'autre librairie d'icônes.
- Utiliser `next/font/google` pour les polices — ne pas linker de CSS externe.

### Don't
- **Ne pas** créer de header sticky local dans une page.
- **Ne pas** ajouter `container mx-auto` en racine de page (utiliser `PageContainer`).
- **Ne pas** dupliquer des boutons de navigation globale dans les pages.
- **Ne pas** hardcoder des couleurs UI alors que le token CSS existe.
- **Ne pas** utiliser les couleurs de graphiques dans l'UI structurelle.
- **Ne pas** introduire de dégradés hors du hero analytique documenté et des remplissages de courbes ; éviter les ombres portées lourdes et les effets "glassmorphism".
- **Ne pas** ajouter d'illustrations décoratives ou de stock photos.
- **Ne pas** implémenter de dark mode — l'application est conçue pour le light mode.
- **Ne pas** créer de nouveau composant de layout sans passer par `AppShell`.
- **Ne pas** ajouter de page sans métadonnées centralisées.
- **Ne pas** modifier l'ordre de navigation sans décision explicite documentée.
- **Ne pas** utiliser de polices autres que Space Grotesk et JetBrains Mono.

## Responsive Behavior

### Breakpoints (Tailwind defaults)

| Name | Width | Key Changes |
|---|---|---|
| Desktop | ≥1024px (lg) | Sidebar visible, header complet, grilles 2-4 colonnes |
| Tablet | ≥768px (md) | Grilles passent de 1 à 2 colonnes |
| Mobile | <768px | Sidebar → drawer, header compact, grilles 1 colonne |

### Mobile Adaptations
- **Sidebar** : devient un drawer (overlay + slide-in), largeur 18rem, max 88vw.
- **Header** : bouton hamburger visible, titre tronqué si nécessaire (`truncate`).
- **Grilles** : forcées en 1 colonne (`grid-cols-1`).
- **Cartes** : padding réduit automatiquement via les classes responsives (`px-4 sm:px-6`).

### Touch Targets
- Boutons : hauteur minimum 2.25rem (h-9) en `sm`, 2.5rem (h-10) en `default`.
- Items de navigation drawer : hauteur minimum 2.75rem (44px) pour le confort tactile.
- Inputs : hauteur 2.5rem minimum.

## Iteration Guide

Ce guide s'adresse à deux publics : les développeurs qui modifient l'UI, et les agents IA qui génèrent du code.

### Pour les développeurs humains

1. **Avant toute modification UI**, lire `docs/style-frontend-ui.md` — c'est la référence normative.
2. Toute nouvelle page suit la procédure en 6 étapes documentée dans ce fichier.
3. Les modifications de navigation passent **exclusivement** par `nav.ts`.
4. Les métadonnées de page passent **exclusivement** par `page-metadata.tsx`.
5. Les couleurs sont **toujours** référencées via les tokens CSS (`globals.css`).
6. Après modification : `cd frontend && npm test && npm run build`.
7. Checklist PR UI obligatoire (voir `docs/style-frontend-ui.md`, section 14).

### Pour les agents IA

1. **Référence toujours les tokens par leur nom** : `bg-card` pas `bg-white`, `text-muted-foreground` pas `text-gray-600`, `border-border` pas `border-gray-300`.
2. **Travaille composant par composant** : termine un `Card` avant d'en commencer un autre. Chaque composant a son token dans la section `components:` du frontmatter YAML.
3. **Quand tu introduis une nouvelle section**, décide d'abord si elle va dans une `Card` existante ou dans une nouvelle `Card`. Les sections ne flottent jamais sans conteneur.
4. **Respecte l'ordre de navigation** : Accueil → Activités → Progression → Objectifs → Traces GPX → Paramètres. Ne réorganise pas.
5. **Le body par défaut est `text-sm` (14px)**, pas `text-base` (16px). CourseScope utilise une échelle légèrement réduite pour la densité d'information.
6. **Ajoute les nouveaux variants comme entrées séparées** dans le frontmatter `components:` si tu crées un nouveau type de composant.
7. **Le bleu marine `primary` est rare** : un seul bouton filled par page. Préfère `outline` ou `ghost` pour les actions secondaires.
8. **N'introduis pas de nouvelle couleur** sans l'ajouter au frontmatter `colors:` et à `globals.css`. Si c'est pour un graphique, utilise les couleurs `chart-*` existantes.

### Vérification post-modification

```bash
cd frontend
npm test
npm run build
```

Vérifier manuellement :
- Desktop : sidebar fixe visible, header cohérent, pas de duplication header/container
- Mobile : drawer fonctionnel, overlay cliquable, touche Escape
- Focus clavier visible sur tous les éléments interactifs
- Aucune couleur hardcodée dans l'UI structurelle

## Agent Prompt Guide

Ce document est conçu pour être lu par des agents IA (Claude, Cursor, Copilot, etc.). Voici un guide rapide pour utiliser ces tokens dans vos prompts.

### Quick Color Reference

| Rôle | Token | Hex | Usage IA |
|---|---|---|---|
| Fond de page | `background` | `#f4f6f9` | `bg-background` sur le body |
| Cartes | `card` | `#ffffff` | `bg-card` sur tout conteneur |
| Texte principal | `foreground` | `#0f172a` | `text-foreground` sur titres/valeurs |
| Texte secondaire | `muted-foreground` | `#475569` | `text-muted-foreground` sur labels |
| Accent primaire | `primary` | `#1d3557` | `bg-primary` sur CTA principale |
| Hover primaire | `primary-hover` | `#27466b` | `hover:bg-primary/90` |
| Bordures | `border` | `#ced8e3` | `border-border` sur cartes/inputs |
| Focus ring | `ring` | `#7890b2` | `focus-visible:ring-ring` |

### Ready-to-Use Prompts

**"Ajoute une carte de métrique (KPI)"**
```
Crée un composant MetricCard avec :
- fond bg-card, border-border, rounded-lg, shadow-sm, p-4
- label en text-xs text-muted-foreground
- valeur en text-2xl font-semibold tabular-nums text-foreground
- unité en text-xs text-muted-foreground
```

**"Ajoute un bouton d'action principale"**
```
Crée un bouton avec :
- bg-primary text-primary-foreground hover:bg-primary/90
- rounded-md, h-10 px-4 py-2
- text-sm font-medium
- focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

**"Ajoute un conteneur de graphique"**
```
Crée une Card avec :
- rounded-lg border bg-card text-card-foreground shadow-sm
- CardHeader avec py-3 px-4, CardTitle en text-base font-semibold
- CardContent avec px-4 pb-4
- le graphique Recharts à l'intérieur
```

**"Ajoute un item dans la sidebar"**
```
Crée un NavItem avec :
- w-full, flex items-center gap-3, rounded-md, px-3 py-2
- icône Lucide à gauche en text-muted-foreground
- libellé en text-sm
- état actif : bg-accent text-foreground + border-l-2 border-primary
- état hover : bg-accent text-accent-foreground
```

**"Ajoute une zone d'upload"**
```
Crée un dropzone avec :
- bg-muted, border-2 border-dashed border-border, rounded-lg, p-8
- texte centré en text-muted-foreground
- état drag : bg-accent border-primary
```

### Structuration d'une nouvelle page

```
1. La page ne contient QUE le contenu métier (pas de header/sidebar/container)
2. Ouvre avec un div.space-y-4
3. Structure le contenu en Cards (Card + CardHeader + CardContent)
4. Utilise grid grid-cols-1 md:grid-cols-2 gap-4 pour les grilles
5. Les KPIs en grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4
6. Déclare les métadonnées dans page-metadata.tsx (pas dans la page)
7. Si la page est dans la nav, modifie nav.ts (pas de lien hardcodé)
```

### Contraintes à respecter

```
- NE PAS utiliser de couleurs hardcodées pour l'UI (toujours les tokens CSS)
- NE PAS créer de header, sidebar, ou container local dans une page
- NE PAS utiliser rounded-xl ou rounded-2xl sur les cartes (rester sur rounded-lg)
- NE PAS ajouter d'ombres lourdes ou de dégradés
- NE PAS implémenter de dark mode
- NE PAS utiliser de polices autres que Space Grotesk et JetBrains Mono
- TOUJOURS utiliser tabular-nums sur les valeurs numériques
- TOUJOURS fournir aria-label sur les boutons icon-only
- TOUJOURS passer npm test && npm run build après modification
```

## Tech Stack Reference

Ce document est lu par des agents IA et des développeurs. Voici les dépendances clés du frontend pour le contexte :

| Catégorie | Technologie | Version | Rôle |
|---|---|---|---|
| Framework | Next.js (App Router) | 16 | Routing, rendu, proxy API |
| UI | React | 19 | Composants |
| Styling | Tailwind CSS | 4 | Utilitaires, tokens |
| Composants | shadcn/ui (adapté) | - | Card, Button (CVA) |
| Icônes | Lucide React | 0.563 | Toute l'iconographie |
| Graphiques | Recharts | 3.7 | Visualisation de données |
| Cartes | Leaflet + react-leaflet | 1.9 / 5.0 | Tracé GPS |
| Requêtes | TanStack React Query | 5.90 | Cache, fetch, mutations |
| State | Zustand | 5.0 | State global |
| 3D (optionnel) | React Three Fiber | 9.5 | Visualisations avancées |
| Forms | react-dropzone | 14.3 | Upload drag & drop |

## Decision Log

### 2025-11-01 — Adoption du shell unique AppShell
- **Contexte** : Les pages dupliquaient headers et containers, créant des incohérences visuelles.
- **Décision** : Centraliser la structure dans `AppShell.tsx` avec métadonnées dans `page-metadata.tsx`.
- **Impact** : Toute nouvelle page doit se conformer à ce contrat. Refacto progressive des pages existantes.

### 2025-12-15 — Palette de couleurs stabilisée
- **Contexte** : Des couleurs arbitraires étaient hardcodées dans les composants.
- **Décision** : Définir les tokens CSS dans `globals.css` et les référencer exclusivement.
- **Impact** : Cohérence visuelle garantie. Changement de thème facilité (un seul fichier).

### 2026-01-20 — Light mode uniquement
- **Contexte** : Question sur l'ajout d'un dark mode.
- **Décision** : Pas de dark mode. Le fond clair est optimal pour la lisibilité des graphiques et cartes.
- **Impact** : Simplification du CSS. Pas de variables `dark:` à maintenir.
