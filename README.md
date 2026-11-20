# Planificateur d'itinéraires de transport — Antananarivo

Planificateur d'itinéraires fondé sur la hiérarchie administrative de Madagascar
(**Région → District / Arrondissement → Commune → Fokontany**). **Entièrement déterministe, sans IA** :
normalisation de chaînes, correspondance exacte / sous-chaîne / table de repères, parcours de graphe borné,
agrégations statistiques.

```
┌──────────────────────────┐   /api/v1 (JSON)   ┌───────────────────────────────────────────┐
│ frontend/  React + TS    │ ─────────────────▶ │ backend/  FastAPI                          │
│ Vite · React Router      │                    │  api/      routeurs, schémas Pydantic      │
│ TanStack Query           │ ◀───────────────── │  engine/   moteur d'itinéraires (domaine)  │
│ servi par nginx (prod)   │                    │  pipeline/ data engineering → processed/   │
└──────────────────────────┘                    └───────────────────────────────────────────┘
```

## Démarrage rapide

### Développement local
Pré-requis : Python ≥ 3.11 et Node ≥ 20.

```bash
make install        # pip install -r backend/requirements-dev.txt  +  npm ci (frontend)
make pipeline       # construit backend/data/processed/ (~8 s)
make api            # http://127.0.0.1:8000/api/v1/docs  (OpenAPI interactif)
make web            # http://localhost:5173  (Vite relaie /api vers le port 8000)
make test           # pytest (28 tests) + typecheck + vitest
```

Sans `make` :
```bash
cd backend  && PYTHONPATH=src python -m planner.pipeline && PYTHONPATH=src uvicorn planner.api.app:app --reload
cd frontend && npm ci && npm run dev
```

### Déploiement sur Vercel ou Netlify
Voir **[DEPLOIEMENT.md](DEPLOIEMENT.md)** : Vercel (site + API, `npx vercel --prod`) ou Netlify (site) + Render (API).

### Déploiement (Docker)
```bash
docker compose up --build      # http://localhost:8080
```
- **backend** : image multi-étapes. L'étape de build exécute le pipeline (pandas/openpyxl) ;
  l'image finale ne contient que l'API et `data/processed/` (utilisateur non-root, healthcheck, 2 workers uvicorn).
- **frontend** : build Vite, puis nginx qui sert la SPA (cache long sur `/assets`, fallback `index.html`)
  et relaie `/api/` vers le backend → même origine, pas de CORS nécessaire.

**Déploiement séparé** (ex. frontend statique sur un CDN, API sur un service de conteneurs) :
construire le frontend avec `VITE_API_BASE_URL=https://api.mondomaine.mg/api/v1`, et lancer le backend avec
`PLANNER_CORS_ORIGINS='["https://mondomaine.mg"]'`.

La CI GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) exécute pipeline, ruff, pytest,
typecheck, vitest, build et `docker compose build`.

## Structure

```
backend/
  data/raw/                 sources : mdg_admin_boundaries.xlsx, liste_bus_antananarivo.txt
  data/reference/           tables ÉDITABLES : manual_places.csv (repères), token_aliases.csv (graphies),
                            line_fokontany.csv (fokontany réellement traversés par chaque ligne)
  data/processed/           généré par le pipeline (tables/, graph/, analysis/) — non versionné
  src/planner/
    settings.py             infrastructure (variables PLANNER_*)
    rules.py                règles métier : confiances, périmètres, poids du score
    core/                   normalisation de texte, géométrie
    pipeline/               admin → bus_parser → matching → geometry → graph → analysis   (python -m planner.pipeline)
    engine/                 repository · search · endpoints (repli) · planner (itinéraires) · service (façade)
    api/                    app (fabrique, lifespan, CORS, gzip) · deps · routers/ · schemas/
    cli.py                  planner pipeline | serve | search | route
  tests/                    texte, sorties du pipeline, moteur, API
frontend/
  src/api/                  client HTTP, types (miroir des schémas), hooks TanStack Query
  src/app/                  App, routeur (pages secondaires chargées à la demande), layout
  src/components/           badges, barres, retours d'état, thème
  src/features/planner/     sélecteur en cascade, recherche, filtres, liste et détail d'itinéraire
  src/features/analysis/    onglet Data Analysis & Couverture
  src/features/network/     lignes, variantes et liaisons
```

## API (`/api/v1`)

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/health`, `/meta` | disponibilité ; chiffres clés et poids du score |
| GET | `/regions` · `/regions/{adm1}/districts` · `/districts/{adm2}/communes` · `/communes/{adm3}/fokontany` | cascade administrative (avec état de desserte) |
| GET | `/fokontany/{adm4}` | fiche : hiérarchie, points du réseau, lignes, repli |
| GET | `/search?q=` | recherche par nom, nom d'arrêt ou `pcode` |
| GET | `/itineraries?from=&to=&max_transfers=` | itinéraires à 0, 1 et 2 correspondances, classés |
| GET | `/network/lines` · `/network/places` | réseau et rattachements |
| GET | `/stats` | statistiques et couverture |

Documentation interactive : `/api/v1/docs` (Swagger) et `/api/v1/redoc`.
L'état de l'interface est dans l'URL (`/?from=MG11118001001&to=MG11117110001&max=1`), donc partageable.

## Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `PLANNER_DATA_DIR` | `backend/data` | racine des données (raw, reference, processed) |
| `PLANNER_CORS_ORIGINS` | `["http://localhost:5173", …]` | origines autorisées (JSON) |
| `PLANNER_ENVIRONMENT` | `development` | libellé d'environnement |
| `VITE_API_BASE_URL` (build front) | `/api/v1` | URL de base de l'API |
| `API_UPSTREAM` (nginx) | `http://backend:8000` | cible du relais `/api/` |

## Règles de rattachement (lieu du corpus → fokontany)

| Ordre | Règle | Statut | Confiance |
|---|---|---|---|
| 0 | Table manuelle `manual_places.csv` (format `Fokontany@Commune`, justification obligatoire) | `repere_ou_variante` | saisie (0,45–0,70) |
| 1 | Nom identique à un fokontany (homonymes départagés par règle) | `exact_fokontany` | 1,00 / 0,85 |
| 1b | « fokontany + commune » ou « commune + fokontany » | `exact_fokontany` | 0,95 |
| 2 | Nom identique à une commune | `commune` | 0,50 |
| 3 | Suite de mots entiers d'un nom de fokontany composé | `sous_chaine_fokontany` | 0,75 / 0,65 |
| 4 | Suite de mots entiers d'un nom de commune | `commune` | 0,40 |
| 5 | Idem après retrait des suffixes (Nord, Sud, Hopitaly…) ; un suffixe directionnel devient un filtre géographique | idem | −0,10 |
| 6 | Seul le qualificatif entre parenthèses est reconnu | `repere_ou_variante` | ≤ 0,45 |
| 7 | Aucune règle applicable | `non_resolu` | 0 |

**Cohérence d'itinéraire (2ᵉ passe)** : un rattachement automatique situé à plus de 3 km de la position moyenne
de ses arrêts voisins sur les lignes est remplacé par un candidat du référentiel nettement plus proche
(ex. *Ambodivona* : fokontany du 6ᵉ écarté au profit d'*Ambodivona Ankadifotsy*, 3ᵉ, à 0,9 km des arrêts voisins).

L'ordre des périmètres dépend du rôle du lieu. Arrêt urbain : Renivohitra, puis périphérie. Terminus suburbain :
périphérie, reste d'Analamanga, Renivohitra, puis Itasy/Vakinankaratra (correspondance exacte uniquement).
Les repères sans preuve (Météo, Anosy, CNAPS, St Antoine…) restent volontairement **non résolus** ; ils servent
quand même de nœuds de correspondance.

## Géométrie et fokontany traversés

- **Coordonnées** de chaque lieu, avec leur qualité (`place_geometry.csv`) : centroïde des fokontany rattachés,
  point de la commune, interpolation à partir des arrêts voisins pour les repères (Météo, Anosy…), ou centre-ville
  pour une gare « Antananarivo (…) » inconnue.
- **Longueur des tronçons** : vol d'oiseau entre arrêts consécutifs. C'est un ordre de grandeur, pas un kilométrage routier.
- **Fokontany traversés** entre deux arrêts (`line_corridors.csv`) :
  `declare` si saisis dans `data/reference/line_fokontany.csv` (prioritaire) ;
  sinon `corridor_estime`, le plus court chemin dans le graphe de voisinage des fokontany, pondéré par la distance.
  Les liaisons suburbaines n'ont **jamais** de fokontany estimés, seulement ceux qui sont déclarés.
  Un fokontany traversé permet de monter ou descendre « en passage » (confiance 0,35 estimé, 0,70 déclaré), jamais
  de faire une correspondance.
- Pour fiabiliser : partir de `data/processed/tables/line_fokontany_suggestions.csv`, valider sur le terrain et
  copier les lignes confirmées dans `data/reference/line_fokontany.csv`.

## Moteur d'itinéraires

- **Accès** : arrêt dans le fokontany, rattachement communal, ligne qui le traverse, **arrêts des fokontany voisins
  à moins de 1,5 km à pied** (toujours proposés, donc accès le plus court), et repli vers les fokontany desservis les plus
  proches (alerte « limite de desserte » au-delà de 6 km).
- **Un itinéraire est toujours proposé**, grâce à une recherche par paliers dont le palier utilisé est affiché :
  1. *normal* : énumération exhaustive à 0, 1 et 2 correspondances depuis les accès ci-dessus ;
  2. *accès élargi* : on ajoute les 12 arrêts les plus proches de chaque extrémité, quelle que soit la distance ;
  3. *approche* : plus court chemin pondéré (Dijkstra, jusqu'à 4 correspondances) vers le point du réseau le plus
     proche de l'arrivée, puis fin du trajet à pied. La marche au-delà de 6 km coûte 10 points par km au lieu de 4.
  Sur 300 couples tirés au hasard dans Analamanga : 0 cas sans itinéraire, 6 ms en moyenne.
- **Recherche** exhaustive à 0, 1 et 2 correspondances (palier normal). Une correspondance se fait au même lieu, ou à pied entre lieux
  du même fokontany.
- **Élimination des trajets inutiles** (comptée et affichée) :
  1. *doublons* : une seule option par suite de lignes ;
  2. *dominés* : sur-ensemble des lignes d'un trajet plus simple ;
  3. *va-et-vient* : trajet qui repasse par un même lieu, s'il existe une alternative propre avec au plus autant de
     correspondances ;
  4. *détours* : distance supérieure à 2,2 fois la distance directe et à la distance directe + 3 km, avec la même condition.
- **Hypothèses explicites** : variante circulaire = sens publié uniquement ; non circulaire = retour *supposé*
  (pénalisé) ; liaison suburbaine = Primus ↔ Terminus seulement, **aucun arrêt intermédiaire inventé**.
- **Score** décomposé et affiché (poids dans `backend/src/planner/rules.py`) :
  `100 − 20×corresp. − 3×corresp. à pied − 5×extrémités à pied − 4×km à pied − 1,2×km en bus − 3×tronçons de longueur inconnue
  − 25×(1 − confiance min.) − 4×tronçons retour − 3×passages terminus − 12×va-et-vient − 0,2×arrêts`.
- **Tri** dans l'interface : recommandé (score), plus court (km), moins de marche, moins de correspondances.
  Les itinéraires « Recommandé » et « Plus court » sont signalés.

## Interface

- La recherche passe d'abord : champs Départ (A) et Arrivée (B) avec autocomplétion (fokontany, arrêt ou `pcode`),
  bouton d'inversion, et cascade Région › District › Commune › Fokontany repliable (« Parcourir la hiérarchie »).
- La recherche démarre automatiquement et l'état est enregistré dans l'URL, donc partageable.
- Le détail se lit en étapes : marcher, prendre la ligne X direction Y, correspondance, descendre. Les arrêts et les
  fokontany traversés sont repliables, et « Pourquoi ce classement ? » détaille le score.
- Responsive :
  - ≥ 1024 px : liste et détail côte à côte, détail collant ;
  - < 1024 px : le détail s'ouvre sous l'itinéraire choisi ;
  - < 760 px : barre de navigation en bas de l'écran ;
  - < 560 px : marges de 16 px et tableaux à défilement horizontal.
- Thème clair, sombre ou automatique ; navigation au clavier (combobox ARIA, lien d'évitement).

## Mettre à jour les données

1. Modifier `backend/data/raw/liste_bus_antananarivo.txt` (nouvelles lignes `LIGNE X`, `* Primus : … -> Terminus : …` ;
   une précision libre commence par `Note :`), compléter `manual_places.csv` ou `line_fokontany.csv`.
2. `make pipeline` (ou reconstruire l'image Docker), puis `make test`.
3. La liste « Lieux non résolus » de l'onglet d'analyse indique les repères les plus utiles à compléter
   (Anosy : 17 lignes, Météo : 12, CNAPS, Rasalama…).
