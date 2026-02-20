# CourseScope - Guide de style Frontend UI

## 1) Objectif de cette note

Ce document est la reference UI pour maintenir une interface homogene dans le temps.

Il definit:
- la structure globale obligatoire (shell)
- les regles de navigation
- les conventions de header et de container
- les regles de composition des pages
- les tokens de design et les usages de couleurs
- la procedure exacte pour ajouter une nouvelle page sans casser la coherence visuelle

Ce guide est normatif: en cas de doute, on suit ce document.

---

## 2) Perimetre et principes directeurs

Perimetre actuel:
- Frontend Next.js App Router sous `frontend/src/app`
- Shell partage sur toutes les pages applicatives
- UI basee sur Tailwind v4 + composants UI existants (`Button`, `Card`)

Principes directeurs:
1. Une seule structure de page globale pour toute l application.
2. Une seule source de verite pour la navigation.
3. Une seule source de verite pour title/subtitle/actions du header.
4. Les pages rendent le contenu metier uniquement.
5. Aucun header local duplique.
6. Aucun container racine local duplique.
7. Les styles utilisent les tokens (`bg-card`, `text-muted-foreground`, etc.), pas des couleurs arbitraires.

---

## 3) Architecture cible (source of truth)

### 3.1 Fichiers structurants

- Shell principal: `frontend/src/components/layout/AppShell.tsx`
- Sidebar: `frontend/src/components/layout/Sidebar.tsx`
- Item de nav: `frontend/src/components/layout/NavItem.tsx`
- Header global: `frontend/src/components/layout/TopHeader.tsx`
- Container global: `frontend/src/components/layout/PageContainer.tsx`
- Config nav: `frontend/src/components/layout/nav.ts`
- Config metadata de page: `frontend/src/components/layout/page-metadata.tsx`
- Actions de header speciales: `frontend/src/components/layout/HeaderActions.tsx`
- Tokens design: `frontend/src/app/globals.css`
- Integration shell: `frontend/src/app/layout.tsx`

### 3.2 Contrat technique

`frontend/src/app/layout.tsx` doit toujours encapsuler les pages comme suit:

```tsx
<Providers>
  <AppShell>{children}</AppShell>
</Providers>
```

Interdiction:
- contourner `AppShell` pour une page standard
- reintroduire un layout local qui re-cree un container global ou un header global

---

## 4) Shell global - specification visuelle et comportementale

### 4.1 Grille generale

Le shell est compose de 2 colonnes:
- colonne gauche: sidebar desktop fixe visuellement
- colonne droite: header + zone de contenu scrollable

Valeurs actuelles (a conserver sauf besoin valide):
- largeur sidebar desktop: `260px`
- hauteur shell: `h-screen`
- scroll principal: dans la zone de contenu droite (`main`)
- scroll sidebar: interne (`overflow-y-auto`)

### 4.2 Sidebar

Structure:
1. bloc haut (branding)
2. nav principale
3. nav footer

Ordre strict des items nav principale:
1. Page d accueil (`/`)
2. Activites (`/activities`)
3. Progression (`/progress`)

Footer:
1. Parametres (`/settings`)

Regles de style:
- item pleine largeur
- icone a gauche, libelle a droite
- hover subtil via tokens muted/accent
- etat actif tres lisible:
  - fond actif (`bg-accent`)
  - indicateur gauche vertical (`bg-primary`)
- focus clavier visible (`focus-visible:ring-2 focus-visible:ring-ring`)

Regle metier importante:
- les routes `/activities/[id]` et `/traces/[id]` activent l item parent correspondant dans la navigation

### 4.3 TopHeader global

Le header global est sticky et contient:
- gauche: `h1` + subtitle optionnel
- droite: info contextuelle optionnelle + actions de page optionnelles
- mobile: bouton menu (ouvre le drawer)

Regles:
- sticky unique en haut de la colonne contenu
- aucune page ne doit re-creer un header sticky local
- actions compactes (`Button size="sm"`)

### 4.4 Drawer mobile

Comportement:
- visible uniquement sur mobile
- overlay cliquable pour fermer
- fermeture par touche `Escape`
- fermeture auto au changement de route

Dimensions:
- largeur: `18rem`
- max largeur: `88vw`

---

## 5) Container global et rythme vertical

Le container global est gere uniquement par `PageContainer`.

Variants autorises:
- `default`: `max-w-6xl`
- `wide`: `max-w-[88rem]`

Padding standard:
- x: `px-4 sm:px-6 lg:px-8`
- y: `py-6`

Regles:
- une page ne doit pas utiliser un root local `container mx-auto ...`
- la page doit demarrer par un wrapper de contenu metier (ex: `space-y-4`)
- l espacement entre sections doit etre coherent (preferer `space-y-4` ou `gap-4`)

---

## 6) Navigation - source unique

Fichier unique: `frontend/src/components/layout/nav.ts`

Schema d un item:

```ts
type NavItemConfig = {
  label: string;
  href: string;
  icon: LucideIcon;
  placement: 'main' | 'footer';
};
```

Regles:
- ne jamais hardcoder la nav dans une page
- ne jamais dupliquer l ordre de nav dans un autre fichier
- tout ajout/suppression/modif de nav passe par `nav.ts`

---

## 7) Header metadata - source unique

Fichier unique: `frontend/src/components/layout/page-metadata.tsx`

Schema:

```ts
type PageMetadata = {
  title: string;
  subtitle?: string;
  container: 'default' | 'wide';
  HeaderActions?: ComponentType;
  showToday?: boolean;
};
```

Regles:
- title/subtitle ne viennent pas des pages, mais du mapping metadata
- les actions specifiques de page vont dans `HeaderActions` (slot du header global)
- les routes dynamiques activity affichent un titre generique (`Activite`) + subtitle selon type

Fallback dynamique actuel:
- `/activities/[id]` -> title `Activite`, subtitle `Analyse reelle`, container `wide`
- `/traces/[id]` -> title `Trace`, subtitle `Analyse theorique`, container `wide`

---

## 8) Regles de composition d une page

Chaque page doit suivre ce contrat:

1. Rendre uniquement le contenu metier.
2. Commencer par un wrapper de contenu (souvent `div.space-y-4`).
3. Utiliser `Card` pour structurer les sections.
4. Utiliser des grilles responsives coherentes (`grid grid-cols-1 md:grid-cols-2 gap-4`).
5. Ne pas recreer:
   - header global
   - nav globale
   - container global

Exceptions legitimes:
- bloc de contexte metier interne (ex: afficher `ID: ...` dans le contenu d une page activity)
- tabs metier internes a une page

---

## 9) Design tokens - palette et usage

Tokens definis dans `frontend/src/app/globals.css`:
- surface: `background`, `card`
- texte: `foreground`, `card-foreground`, `muted-foreground`
- etats et interactions: `accent`, `primary`, `secondary`
- structure: `border`, `input`, `ring`
- erreur: `destructive`

Regles d usage:
1. Toujours preferer classes tokenisees (`bg-card`, `text-muted-foreground`, `border-input`).
2. Eviter les couleurs hardcodees pour UI structurelle.
3. Couleurs hardcodees tolerables uniquement pour visualisation data (charts), si necessaire.
4. Le contraste texte secondaire doit rester lisible (pas de gris trop faible).

---

## 10) Typographie, densite, cards

Typographie:
- titre de page: `text-2xl font-semibold tracking-tight`
- subtitle de page: `text-sm text-muted-foreground`
- titre de card: `text-base` (via `CardTitle` adapte)
- labels secondaires: `text-xs` ou `text-sm text-muted-foreground`
- valeurs numeriques importantes: `font-semibold tabular-nums`

Cards:
- base: `rounded-lg border bg-card text-card-foreground shadow-sm`
- header compact courant: `CardHeader className="py-3 px-4"`
- content courant: `CardContent className="px-4 pb-4"`

Rythme:
- entre cards: `space-y-4`
- dans une ligne de cards: `gap-4`

---

## 11) Accessibilite et UX (non negociable)

Checklist A11y minimale:
- focus visible sur items nav et boutons (ring token)
- labels `aria-label` sur boutons icon-only
- navigation clavier possible dans sidebar et header
- contraste lisible (texte principal et texte muted)
- structure semantique correcte (`header`, `main`, `nav`)
- drawer mobile ferme via overlay et `Escape`

UX globale:
- scroll sidebar et scroll contenu independants
- pas de jitter visuel sur header sticky
- comportement mobile utilisable sans zoom horizontal

---

## 12) Procedure pour ajouter une nouvelle page

Objectif: ajouter une page en conservant 100% de coherence visuelle.

### Etape 1 - Creer la route

Exemple: `frontend/src/app/reports/page.tsx`

Regle:
- composant page centre sur contenu metier
- pas de header local global
- pas de container root local

### Etape 2 - Declarer le metadata de page

Dans `frontend/src/components/layout/page-metadata.tsx`:

```ts
'/reports': {
  title: 'Reports',
  subtitle: 'Analyse et exports',
  container: 'default',
}
```

Option:
- `container: 'wide'` pour pages denses en graphiques/tableaux

### Etape 3 - Ajouter la page dans la navigation (si besoin)

Dans `frontend/src/components/layout/nav.ts`:

```ts
{
  label: 'Reports',
  href: '/reports',
  icon: SomeIcon,
  placement: 'main', // ou 'footer'
}
```

Important:
- respecter l ordre produit decide
- ne pas casser l ordre strict existant sans decision explicite

### Etape 4 - Ajouter des actions de header (si besoin)

Creer une action dediee dans `frontend/src/components/layout/HeaderActions.tsx` (ou fichier voisin):

```tsx
'use client';

export function ReportsHeaderActions() {
  return <Button size="sm" variant="outline">Exporter</Button>;
}
```

Puis brancher dans metadata:

```ts
'/reports': {
  title: 'Reports',
  subtitle: 'Analyse et exports',
  container: 'default',
  HeaderActions: ReportsHeaderActions,
}
```

Regle:
- les actions doivent vivre dans le slot du header global
- ne pas replacer ces boutons dans un faux header local

### Etape 5 - Composer le contenu avec les primitives UI

Recommandation:
- sections principales en `Card`
- grilles responsives `grid-cols-1 md:grid-cols-2` selon besoin
- espacement constant `space-y-4`

### Etape 6 - Verifier

Commandes minimales:
- `cd frontend && npm test`
- `cd frontend && npm run build`

Controle manuel:
- desktop: sidebar fixe, header coherent
- mobile: drawer ok
- focus clavier visible
- aucune duplication header/container

---

## 13) Anti-patterns a refuser en review

1. Ajouter un header sticky local de page.
2. Ajouter `container mx-auto ...` en root de page.
3. Dupliquer des boutons de navigation globale dans les pages.
4. Hardcoder des couleurs UI alors que le token existe.
5. Ajouter une route sans metadata centralisee.
6. Ajouter un item de nav en dehors de `nav.ts`.
7. Ajouter des actions de page hors slot de header global.

---

## 14) Checklist PR UI (obligatoire)

Avant merge, verifier:

- [ ] La page est bien enveloppee par `AppShell` (pas de contournement).
- [ ] `title/subtitle` viennent de `page-metadata.tsx`.
- [ ] Navigation modifiee uniquement via `nav.ts`.
- [ ] Aucune duplication de header/container dans la page.
- [ ] Les cards et espacements suivent le rythme global (`space-y-4`, `gap-4`).
- [ ] Les classes utilisent les tokens design existants.
- [ ] Le comportement mobile drawer est intact.
- [ ] Accessibilite clavier et focus visible ok.
- [ ] `npm test` passe.
- [ ] `npm run build` passe.

---

## 15) Decision log UI future (recommande)

Pour garder un fil conducteur dans le temps:
- documenter chaque changement de direction UI dans une section "Decision" en fin de ce fichier
- inclure: date, raison, impact, migration necessaire

Format recommande:

```md
### Decision YYYY-MM-DD - Titre court
- Contexte:
- Decision:
- Impact:
- Actions de migration:
```

---

## 16) Resume rapide pour un nouveau dev

Si tu ajoutes une page:
1. Cree la route.
2. Ajoute son metadata central.
3. Ajoute la nav si necessaire.
4. Branche les actions de header via slot.
5. Compose le contenu metier en cards, sans header/container dupliques.
6. Passe tests + build.

Si tu respectes ces 6 points, l app restera homogene.
