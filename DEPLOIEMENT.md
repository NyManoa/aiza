# Déploiement — Vercel ou Netlify

L'application a deux parties : le **site** (React, fichiers statiques) et l'**API** (FastAPI, Python).

| Option | Site | API | Adresse | Quand la choisir |
|---|---|---|---|---|
| **A. Vercel** (recommandée) | Vercel | Vercel (fonction Python) | une seule, `/api` sur le même domaine | le plus simple : un seul projet |
| **B. Netlify + Render** | Netlify | Render (conteneur Docker) | Netlify relaie `/api/*` vers Render | si vous tenez à Netlify (qui n'exécute pas de Python) |

Fichiers fournis : `vercel.json`, `api/index.py`, `requirements.txt`, `.vercelignore` (option A) ;
`netlify.toml`, `render.yaml`, `backend/Dockerfile` (option B).

## 0. Préparer (dans tous les cas)

```bash
make install          # dépendances Python (dev) et Node
make deploy-check     # régénère backend/data/processed, lance les tests, construit le site
```

Le dossier `backend/data/processed/` (≈ 4 Mo) **doit être présent**, car l'API sur Vercel le lit. Il est versionné
(voir `.gitignore`). Après chaque modification de `backend/data/raw/` ou `backend/data/reference/`, relancez
`make pipeline` puis redéployez.

Pour un déploiement automatique à chaque `git push`, le code doit être sur GitHub, GitLab ou Bitbucket :
```bash
git init && git add -A && git commit -m "Planificateur de transport"
git branch -M main
git remote add origin https://github.com/<vous>/<depot>.git
git push -u origin main
```

## Option A — Vercel (site + API)

### A1. En ligne de commande
```bash
npx vercel login              # une fois
npx vercel                    # 1er déploiement : crée et lie le projet, donne une URL de prévisualisation
npx vercel --prod             # mise en production (https://<projet>.vercel.app)
```
Au premier `npx vercel`, répondre : *Set up and deploy* → **Yes** ; *Link to existing project* → **No** ;
nom du projet → au choix ; *In which directory is your code located?* → **./** ;
*Modify settings?* → **No** (tout est dans `vercel.json`).
Raccourcis : `make vercel` (prévisualisation) et `make vercel-prod` (production), qui vérifient d'abord les données,
les tests et le build.

### A2. Depuis Git (déploiement automatique)
1. Sur vercel.com, ouvrir **Add New… → Project**, puis importer le dépôt.
2. *Framework Preset* : **Other** ; *Root Directory* : la racine du dépôt. Les commandes viennent de `vercel.json`.
3. Cliquer sur **Deploy**. Ensuite, chaque push sur `main` part en production et chaque branche ou PR obtient une
   prévisualisation.

### A3. Vérifier
- `https://<projet>.vercel.app/api/v1/health` doit renvoyer `{"status":"ok"}`.
- `https://<projet>.vercel.app/api/v1/docs` affiche la documentation de l'API.
- `https://<projet>.vercel.app/` affiche le site ; une recherche doit afficher des itinéraires.

Aucune variable d'environnement n'est nécessaire : site et API partagent le même domaine, donc pas de CORS.

## Option B — Netlify (site) + Render (API)

### B1. API sur Render
1. Sur render.com, ouvrir **New → Blueprint**, choisir le dépôt, puis **Apply**. Le fichier `render.yaml` est lu
   automatiquement ; l'image est construite depuis `backend/Dockerfile`, qui exécute le pipeline pendant le build.
2. Noter l'URL, par exemple `https://tana-planner-api.onrender.com`, et vérifier `…/api/v1/health`.
   En offre gratuite, le service s'endort après environ 15 minutes d'inactivité ; la première requête prend
   ensuite 30 à 60 s.

### B2. Site sur Netlify
1. Dans `netlify.toml`, remplacer `https://VOTRE-API.onrender.com` par l'URL de l'étape B1.
2. En ligne de commande :
   ```bash
   npx netlify login                    # une fois
   npx netlify init                     # crée/lie le site (ou : npx netlify link)
   npx netlify deploy --build           # prévisualisation   (ou : make netlify)
   npx netlify deploy --build --prod    # production         (ou : make netlify-prod)
   ```
   Depuis Git : sur app.netlify.com, ouvrir **Add new site → Import an existing project**, puis choisir le dépôt.
   Les réglages (base `frontend`, commande, dossier `dist`, redirections) viennent de `netlify.toml`.
3. Vérifier `https://<site>.netlify.app/api/v1/health` (relayé vers Render), puis le site.

Variante : l'API peut aussi être déployée sur Vercel (option A) et le site sur Netlify. Il suffit de mettre l'URL
Vercel dans la redirection `/api/*` de `netlify.toml`.

## Mettre à jour après une modification des données

```bash
# 1. modifier backend/data/raw/liste_bus_antananarivo.txt (et l'ENREGISTRER) ou data/reference/*.csv
make pipeline && make test
# 2. redéployer
git add -A && git commit -m "Mise à jour des lignes" && git push      # déploiement Git (Vercel / Netlify / Render)
# ou : make vercel-prod   |   make netlify-prod
```

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Le site s'affiche mais « L'API est-elle disponible ? » | redirection `/api` incorrecte | Vercel : vérifier `vercel.json` ; Netlify : URL de l'API dans `netlify.toml` |
| `/api/v1/health` renvoie 500 avec « network.json introuvable » | `backend/data/processed` absent du déploiement | `make pipeline`, le committer (ou vérifier `.vercelignore`), redéployer |
| Page 404 en rechargeant `/analyse` | réécriture SPA absente | les règles `index.html` de `vercel.json` / `netlify.toml` doivent être présentes |
| Première requête très lente (Render gratuit) | service endormi | normal en offre gratuite ; passer à une offre payante pour l'éviter |
