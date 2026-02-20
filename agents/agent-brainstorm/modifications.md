# CourseScope - Modifications (agent-brainstorm)

Repo local: `C:\Users\domin\Documents\Python Scripts\CourseScope`
Repo github: `https://github.com/kolokolone/CourseScope`

Contrainte (phase brainstorm): ne pas toucher au code applicatif ici; decrire les modifications a faire dans `docs/modifications.txt` et donner des details d'implementation coherents avec le code existant.

Sources a respecter:
- UI: `docs/style-frontend-ui.md`
- Scope fonctionnel: `docs/modifications.txt`

Fichiers clefs (points d'ancrage dans l'architecture):
- `frontend/src/app/goals/page.tsx` (timeline objectifs + CRUD)
- `frontend/src/app/page.tsx` (page d'accueil)
- `frontend/src/app/settings/page.tsx` (parametres)
- `frontend/src/components/layout/AppShell.tsx` (wiring header global + showToday)
- `frontend/src/components/layout/TopHeader.tsx` (rendu header)
- `frontend/src/components/layout/page-metadata.tsx` (config title/subtitle/container/showToday)
- `frontend/src/app/traces/[id]/page.tsx` (page trace/theorique, input allure + graph)
- `frontend/src/components/charts/TheoreticalPaceElevationChart.tsx` (graph "Allure vs distance")
- `backend/api/main.py` (version API exposee)

---

## 1) Sur la page "Objectifs" (`/goals`)

### 1.1 Ligne temporelle: idee plus performante + range dynamique

Etat actuel (ce qui existe)
- `Timeline` est un composant interne dans `frontend/src/app/goals/page.tsx`.
- Placement:
  - tri par date
  - normalisation `pos` entre today et end
  - 2 lanes maximum via une heuristique "dense -> alterne haut/bas".
- Range:
  - `today = startOfDay(new Date())`
  - `lastDate = max(dates) ou today`
  - `end = addMonths(lastDate, 1)`

Changement demande (range)
- Au lieu de "+ 1 mois", garder seulement "+ 1 semaine" apres la derniere date d'evenement.

Implementation recommandee (simple, sans changer le style)
- Dans `frontend/src/app/goals/page.tsx`:
  - remplacer l'usage de `addMonths(lastDate, 1)` par une helper `addDays(lastDate, 7)`.
  - regles:
    - si aucun objectif: `end = today + 7 jours`
    - si `lastDate < today`: `end = today + 7 jours` (sinon tous les events se retrouvent a `pos=0`)
  - conserver le clamp de `pos`.

Amelioration "auto-layout" (le vrai point "plus performant")
- Objectif: eviter les chevauchements de cartes quand plusieurs evenements sont proches.
- Rester en rendu custom (le plus coherent avec l'UI actuelle) mais ameliorer l'assignation de lane:
  - etape 1: estimer une distance minimale entre cartes en X.
    - la carte fait `w-44` (~176px). Avec `minWidthPx` du container, tu peux transformer 176px en delta `pos`.
  - etape 2: greedy lane assignment:
    - trier par `pos`
    - pour chaque event, placer dans la premiere lane dont le dernier `pos` est assez loin
    - sinon, creer une 3e lane
  - etape 3 (degradation): limiter a 3 lanes, puis stack/compact si trop dense.

Ticks: mois -> semaines
- La timeline affiche aujourd'hui un quadrillage mensuel.
- Avec un range plus court (souvent quelques semaines), le plus lisible est:
  - ticks hebdo (ex: lundi) + labels "Semaine du ..."
  - eventuellement 1 tick "aujourd'hui" distinct (marqueur)

Idees "librairie" (si tu veux tester)

Option A (recommandee): garder la timeline custom, utiliser une mini-lib pour les echelles/ ticks
- `d3-scale` + `d3-time` (ou `date-fns`) pour:
  - convertir date -> x
  - generer des ticks (jours/semaines/mois)
- Avantage: pas de rupture UI, ajout leger.

Option B (plus lourde): timeline complete
- `react-calendar-timeline` ou `vis-timeline`.
- Avantages: collisions/zoom geres.
- Inconvenients: style + CSS a re-travailler pour rester coherent avec `docs/style-frontend-ui.md`.

Acceptance criteria
- Range: fin = `derniere_date + 7 jours`.
- Les cartes restent lisibles (pas de recouvrement evident) sur desktop.
- Le style actuel (cartes + pointille bleu + point blanc) est conserve.

---

### 1.2 Ajouter un calendrier tres simple sous la timeline (test)

Demande
- Calendrier en grille, traits fins gris.
- Reutiliser les cartes evenements de la timeline a l'interieur d'une case.
- Debut: aujourd'hui.
- Fin: 1 semaine apres le dernier evenement.
- Dynamique (adaptation selon dates).

Proposition d'implementation

Structure UI
- Ajouter un `Card` sous `Timeline` dans `frontend/src/app/goals/page.tsx`.
- Titre: "Calendrier des objectifs".

Modele de donnees
- `start = startOfDay(new Date())`
- `end = startOfDay(lastEventDate) + 7 jours` (meme regle que la timeline)
- Construire une liste `days[]` avec un item par date.
- Indexer les objectifs par `event_date` (cle ISO `YYYY-MM-DD`) pour insertion O(1) par jour.

Rendu grille
- CSS grid 7 colonnes (lun->dim) en desktop.
- Cellules:
  - label date en haut a gauche (text-xs muted)
  - contenu: 0..N cartes.
- Reutilisation des cartes:
  - extraire le rendu carte (nom/date/distance/type) dans un petit composant (ex: `GoalMiniCard`) pour etre utilise a la fois dans la timeline et le calendrier.

Cas limites
- Range trop long:
  - imposer un max (ex: 12 semaines)
  - ou pagination par semaine.

Acceptance criteria
- La grille commence aujourd'hui et se termine `lastEvent + 7j`.
- Le style des mini-cartes est identique a celui de la timeline.

---

### 1.3 Etat vide: corriger le bug du logo "barre" (overlay decale)

Demande
- Corriger le bug ou un 2e element (l'effet "barre") apparait a cote du logo.

Etat actuel
- `frontend/src/app/goals/page.tsx` (etat vide): icone `Target` + icone `CircleOff` positionnee en `absolute -right-1 -top-1`.

Fix recommande
- Objectif visuel: un seul "logo barre" centre.
- Option la plus robuste (sans dependances): remplacer l'overlay icone par une simple barre CSS centree:
  - garder `Target` centre
  - ajouter un `div` absolu (slash) centre
  - supprimer/eviter l'icone overlay qui se place en badge.

Acceptance criteria
- Un seul bloc centre (pas de 2e element a cote).
- Rendu identique desktop/mobile.

---

## 2) Sur la page d'accueil (`/`)

### 2.1 Carte "prochain objectif" quand il existe des objectifs

Demande
- Si pas d'objectifs: ne rien faire.
- Sinon: afficher une carte carree (pas trop grande) montrant:
  - "Prochain objectif dans :" (gris)
  - `J-X` (gros, centre)
  - details: Nom, date, distance, type.

Ou implementer
- `frontend/src/app/page.tsx`.
- Donnees: `useGoalsList()` (dans `frontend/src/hooks/useGoals.ts`).

Selection du prochain objectif
- Definir `todayStart = startOfDay(new Date())`.
- Filtrer `event_date >= todayStart`.
- Trier par date croissante.
- Choisir le premier.
- Si aucun objectif futur: ne rien afficher (comportement le plus safe).

UI proposee (coherente avec la page)
- Conserver les 2 cartes d'upload en haut.
- Ajouter en dessous une zone ou la carte peut "se poser" a droite sur desktop:
  - layout possible: `grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4`
  - la carte objectif dans la colonne droite.
- Carte:
  - `Card` + `aspect-square` + `max-w` (ex: 18-20rem)
  - contenu centre, `tabular-nums` pour le decompte
  - details en style proche des cartes timeline (mais idealement tokenise).

Acceptance criteria
- Rien ne change si pas d'objectifs.
- Carte visible et stable quand il existe un objectif futur.

---

## 3) Sur la page des parametres (`/settings`)

### 3.1 Ajouter une mention de version (backend)

Demande
- Afficher la version en haut, a droite du titre "Parametres".
- Meme police que "Configuration de l'application" (subtitle).

Etat actuel
- Backend:
  - `backend/api/main.py` definit `version="1.1.69"`.
  - `GET /` renvoie aussi `{ "version": "1.1.69", ... }`.
- Frontend:
  - le header global est gere par `AppShell` + `TopHeader`.
  - pas de champ "version" expose dans l'UI.

Implementation recommandee

Backend
- Minimal: reutiliser `GET /` (pas d'ajout serveur).
- Alternatif plus propre: ajouter `GET /version` ou `GET /meta` (retour `{ version }`).

Frontend
- Ajouter un petit appel API dans `frontend/src/lib/api.ts` (ex: `metaApi.root()` ou `metaApi.version()`).
- Dans `frontend/src/app/settings/page.tsx`, `useQuery` pour recuperer la version.
- Affichage dans le header global (pas dans le contenu de la page):
  - option 1: passer par `HeaderActions` dans `frontend/src/components/layout/page-metadata.tsx` (car `contextInfo` force une taille `text-xs` aujourd'hui).
  - option 2: etendre `PageMetadata` avec un champ specifique et l'afficher via `AppShell`.

Acceptance criteria
- Version visible sur `/settings`, alignee a droite du titre.
- Valeur vient bien du backend.

---

## 4) Sur la page "Progression" (`/progress`) et header global

### 4.1 Date top-right: centrer la hauteur (sans toucher la fonction)

Etat actuel
- La date est construite dans `frontend/src/components/layout/AppShell.tsx` via `formatTodayLabel()`.
- Elle est rendue dans `frontend/src/components/layout/TopHeader.tsx` en `contextInfo`.
- Le layout parent utilise `items-start`, donc le bloc droit est en haut.

Fix de layout propose
- Garder `formatTodayLabel()` intact.
- Modifier uniquement la mise en page dans `frontend/src/components/layout/TopHeader.tsx`:
  - ajouter `self-center` au bloc droit qui contient `contextInfo` et `actions`.
  - alternative: remplacer `items-start` par `items-center` sur le container principal (a tester avec subtitle).

Acceptance criteria
- Sur `/progress`, la date est visuellement centree verticalement dans le header.

---

### 4.2 Afficher cette date sur toutes les pages (sauf Parametres)

Etat actuel
- `showToday` n'est active que pour `/progress` dans `frontend/src/components/layout/page-metadata.tsx`.

Implementation proposee
- Dans `frontend/src/components/layout/page-metadata.tsx`:
  - activer `showToday: true` pour:
    - `'/'`, `'/activities'`, `'/goals'`, `'/traces'`
  - activer aussi sur les routes dynamiques:
    - fallback `isDynamicRealActivityRoute()`
    - fallback `isDynamicTraceRoute()`
  - ne pas activer sur `'/settings'`.

Note mobile
- Le `contextInfo` est masque en dessous de `sm` (`hidden ... sm:inline`).
- Si tu veux la date sur mobile aussi, il faudra ajuster ce point (non demande explicitement).

Acceptance criteria
- Sur desktop: date presente sur toutes les pages, sauf `/settings`.

---

## 5) Sur la page d'une trace (`/traces/[ID]`) (analyse theorique)

### 5.1 Default allure cible = 75% VMA (sinon 05:00)

Etat actuel
- `paceInput` et `applied.pace` sont initialises a `5:00`.
- VMA est lue via `usePersonalSettings()` et envoyee au backend.

Implementation proposee
- Calcul:
  - `speed_kmh = 0.75 * vma_kmh`
  - `pace_s_per_km = 3600 / speed_kmh`
  - formater en `mm:ss`.
- Appliquer le default des que la VMA est disponible, mais sans ecraser une saisie utilisateur:
  - ajouter un flag "userTouchedPace".

Acceptance criteria
- VMA presente -> default calcule.
- VMA absente -> 5:00.
- Saisie utilisateur preservee.

---

### 5.2 Graph "Allure vs distance": meilleure estimation (allure cible + VMA + pente)

Etat actuel
- Backend: `backend/api/routes/analysis.py` calcule les segments avec `grade_factor()` + `vma_factor`.
- `grade_factor()` v1 est dans `backend/core/grade_table.py`.

Pistes d'amelioration (sans casser l'API)

Option A (recommandee): modele "effort constant"
- Interpretrer l'allure cible comme un effort relatif (via VMA) puis appliquer une correction de pente energetique (type Minetti).
- Avantage: plus "physio" et plus stable qu'un simple scaling global.
- option A à intégrer

Option B (incrementale): garder grade_factor, reduire la dependence a `vma_factor`
- VMA sert deja a definir l'allure cible par defaut; ensuite, l'utilisateur fixe son allure.
- Ameliorer downhill (actuel: inverse + clamp) pour eviter des gains trop agressifs.
- option B à éviter

Acceptance criteria
- Sur plat: courbe proche de l'allure cible.
- En pente: transitions lisses, pas d'artefacts.
- Descente: gains limites, pas d'allures irreelles.

---

### 5.3 Slider vertical pour le zoom de l'axe Y (lisibilite)

Etat actuel
- `frontend/src/components/charts/TheoreticalPaceElevationChart.tsx` utilise `domain={['dataMin','dataMax']}`.

Implementation proposee
- Ajouter un slider vertical (range, 2 thumbs) a gauche du chart.
- Domaine initial: min/max (idealement robust quantiles pour limiter outliers).
- Lors du drag: mettre a jour le `domain` de `YAxis`.
- Implementation slider:
  - soit introduire Radix Slider et creer `frontend/src/components/ui/slider.tsx`
  - soit un composant custom minimal.

Acceptance criteria
- L'axe Y change sans lag.
- Slider intuitif malgre `reversed`.

---

## Prompt (optionnel) pour implementer ces modifications

Respecte `docs/style-frontend-ui.md` (pas de header/container dupliques). Implemente:
1) `/goals`: range timeline = `lastEvent + 7j`, meilleur auto-layout, calendrier simple sous la timeline, fix etat vide "logo barre".
2) `/`: afficher une carte "Prochain objectif" si un objectif futur existe (J-X + details).
3) `/settings`: afficher la version backend dans le header, a droite du titre.
4) Header global: afficher la date sur toutes les pages sauf settings; aligner verticalement la date.
5) `/traces/[id]` (theorique): default allure = 75% VMA sinon 5:00; ameliorer le modele de pente cote backend; ajouter un slider vertical pour l'axe Y du graph "Allure vs distance".

## Après les changements de code
- Faire un bump de version 
- Faire un git commit et push sur github
- lancer le workflow de création de l'image docker
