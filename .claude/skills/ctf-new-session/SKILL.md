---
name: ctf-new-session
description: Préparer une nouvelle session du DuckDB SQL CTF — recaler la date et le lieu, régénérer les données, redéployer la stack et publier le nouveau journal. À utiliser dès que l'utilisateur dit "nouvelle session du CTF", "on donne le CTF le <date>", "préparer le CTF à <ville>", ou demande de mettre à jour les coordonnées GPS, la date de mort de Quackie, ou le journal Le Canard Enchaîné. Concerne le repo duckdb-sql-ctf (DuckDB CTF).
---

# CTF — Nouvelle session

Workflow pour préparer une nouvelle session du CTF DuckDB. L'objectif est de modifier le minimum de fichiers pour caler la date et le lieu, puis de redéployer.

> **Pourquoi ce skill existe** : entre deux sessions, presque tout reste stable (noms "du Lac", emails, employeurs, scénarios markdown). Seuls la date et les coordonnées bougent. Ce skill encapsule cette discipline et empêche de toucher à des choses qui n'ont pas besoin de l'être.

## Étape 1 — Vérifier les accès

À faire avant tout (cf. CLAUDE.md du repo : Terraform commands lit `.env` à la racine pour AWS + PG).

```bash
# Git
git remote -v   # doit pointer vers Jeremynadal33/duckdb-sql-ctf

# AWS via .env (les credentials SSO viennent de là)
set -a && source .env && set +a && aws sts get-caller-identity
```

Si `aws sts` renvoie `ExpiredToken` : demander à l'utilisateur de rafraîchir son SSO (suggérer `! aws sso login --profile ctf` qu'il tape lui-même), et **attendre** sa confirmation avant de continuer. Ne pas tenter de relancer le login soi-même.

## Étape 2 — Récolter les infos minimales

Poser **uniquement** ces 3 questions (utiliser AskUserQuestion pour les 1+2, texte libre pour la 3) :

1. **Date du CTF** (jour exact). Calculer :
   - `TARGET_DATE = <date du CTF>`
   - `QUACKIE_DEATH_DATE = TARGET_DATE - 30 jours` (toujours ; c'est dérivé dans `constants.py`, pas un input)

2. **Lieu du CTF** : ville + adresse précise. Cette adresse devient la **planque finale** de Hugh Quackman (constants `TARGET_*`). Demander une adresse *précise* (rue + numéro + code postal) car le scénario 6 fait un reverse-geocoding via Nominatim — si la lat/lon n'est pas exactement sur l'adresse, le résultat sera flou.

3. **Decoy** (à confirmer rapidement, défaut auto-déduit) :
   - CTF à **Bordeaux** → decoy = **Paris** (Bassin de la Villette)
   - CTF à **Paris** → decoy = **Bordeaux** (Lac de Bordeaux)
   - CTF **ailleurs** (Lyon, Nantes, etc.) → decoy = **Bordeaux** (default fallback ; ne jamais demander de 3e jeu d'adresses)

   Si l'utilisateur veut overrider (rare), accepter ses adresses spécifiques.

Charger `references/default-locations.md` pour les coordonnées par défaut Paris et Bordeaux.

## Étape 3 — Modifier les fichiers

Liste **exhaustive** et **minimale**. Tout le reste reste stable d'une session à l'autre — ne pas toucher.

### 3.1 — `data_generator/src/data_generator/constants.py`

Modifier uniquement :
- `TARGET_DATE = date(YYYY, M, D)` (la date du CTF)
- 5 blocs `LIBRARY_*`, `ARCHIVES_*`, `CITY_HALL_*`, `QUACKIE_*` (decoy / scène) + `TARGET_*` (planque)

Pour chaque bloc : `*_CITY = "..."`, `*_LAT = ...`, `*_LON = ...`.

`QUACKIE_DEATH_DATE` est dérivé automatiquement (`TARGET_DATE - timedelta(days=30)`) — ne pas le toucher.

### 3.2 — Journal `docs/le-canard-enchaine-*.md`

Le flag scénario 3 pointe vers ce fichier sur GH Pages (cf. `generators/scenario3_postgres.py:build_scenario3_flag` qui construit le nom à partir de `QUACKIE_DEATH_DATE`).

1. Supprimer l'ancien : `rm docs/le-canard-enchaine-<JJ-mois-AAAA>.md`
2. Créer le nouveau avec le filename `le-canard-enchaine-<jour>-<mois en français minuscule>-<année>.md`. Mois français : janvier, février, mars, avril, mai, juin, juillet, août, septembre, octobre, novembre, décembre.

Template (adapter ville et date dans le titre + dans le dateline en gras) :

```markdown
# LE CANARD ENCHAÎNÉ — <JJ mois AAAA>

---

## FAITS DIVERS

### Un médecin du Lac retrouvé sans vie : accident de chasse ou règlement de comptes ?

**<Ville decoy>** — Le Dr. Quackie Chan, 47 ans, médecin généraliste à la Clinique du Lac et employé de longue date de la Bibliothèque du Lac, a été retrouvé sans vie dimanche dernier dans les marais bordant le Lac. Les premiers éléments de l'enquête privilégient la piste d'un accident de chasse, bien que plusieurs témoins aient signalé des allées et venues inhabituelles dans le secteur les jours précédents.

Le Dr. Chan, décrit par ses collègues comme « discret mais apprécié », travaillait à la bibliothèque depuis près de huit ans. Son badge d'accès — BADGE-0042 — était encore actif au moment de la découverte du corps.

> *« C'est incompréhensible »*, confie un collègue sous couvert d'anonymat. *« Quackie n'avait pas d'ennemis. Et surtout, son badge a continué d'être utilisé après sa disparition. Quelqu'un s'en est servi. »*

Les enquêteurs du C.A.C. ont ouvert une investigation pour déterminer qui a pu utiliser le badge du défunt médecin. Les archives d'accès pourraient s'avérer déterminantes — à condition de remonter suffisamment loin dans le temps.

---

*Édition spéciale — Rubrique « Là où ça canarde »*
```

Notes :
- Garder "du Lac" partout (générique, ne dépend pas de la ville).
- Seules les mentions à modifier sont **la date du titre** et **la ville decoy** dans le `**<Ville decoy>** — Le Dr....`.

### 3.3 — `docs/solutions.md`

Trois modifs ciblées (rechercher avec Edit, pas réécrire le fichier) :
- Le couple `'lat': '...'` / `'lon': '...'` dans la requête Nominatim → mettre les nouvelles coords **Quackie** (decoy).
- `where city_name = '...'` → mettre la ville **decoy**.
- `TIMESTAMP '<YYYY-MM-DD> 00:00:00'` dans la requête iceberg → mettre `QUACKIE_DEATH_DATE`.

### 3.4 — `docs/map/map.js`

5 fallbacks à mettre à jour (les valeurs après `??`) :
- `library`, `city_hall`, `quackie` → coords + `sublabel` decoy
- `target` → coords + `sublabel` ville du CTF (planque)

`locations.js` est régénéré automatiquement à l'étape suivante — ne pas l'éditer à la main.

### 3.5 — Régénérer `locations.js`

```bash
mise run generate:locations
```

Doit produire `docs/map/locations.js` cohérent avec `constants.py`.

### 3.6 — Recaler `docs/agent.js` sur l'API Gateway courante

`docs/agent.js` contient une constante `API_URL` hardcodée vers l'API Gateway (`https://<id>.execute-api.eu-west-1.amazonaws.com/`). Si la stack a été détruite/recréée entre deux sessions, l'ID de l'API a changé et le frontend appelle un endpoint mort (inscription des joueurs cassée).

Récupérer la valeur courante depuis Terraform et l'écrire dans `agent.js` :

```bash
set -a && source .env && set +a
API_URL=$(terraform -chdir=terraform output -raw api_gateway_url)
echo "Current API: $API_URL"
```

Puis mettre à jour la ligne `const API_URL = '...';` dans `docs/agent.js` (Edit ciblée, pas de réécriture). Vérifier ensuite par grep qu'il ne reste qu'une seule occurrence avec la nouvelle valeur.

## Étape 4 — Tests + redéploiement

À ce stade, vérifier que rien d'autre n'a été modifié par erreur :

```bash
git status --short
git diff --stat
```

Le diff attendu : **uniquement** `constants.py`, `solutions.md`, `map.js`, `locations.js`, `agent.js`, l'ancien journal en suppression, le nouveau journal en untracked. Si autre chose apparaît, enquêter avant de continuer.

### 4.1 — Tests unitaires

```bash
cd data_generator && uv run pytest tests/ -v
```

Attendu : 47 passed, 2 skipped (les solutionators scenario3/6 sont skip car ils requièrent une infra live). Si un test échoue, ne pas continuer.

### 4.2 — Nettoyer les buckets S3

À supprimer (anciennes inscriptions / soumissions / leaderboard) :

```bash
set -a && source .env && set +a
aws s3 rm s3://duckdb-sql-ctf/leaderboard/snapshot.parquet
aws s3 rm s3://duckdb-sql-ctf/user-inputs/ --recursive
aws s3 rm s3://duckdb-sql-ctf/leaderboard/ctf-events/ --recursive
```

> **Ne pas toucher** `s3://duckdb-sql-ctf/leaderboard/answers/` (flags managés par Terraform) ni `s3://duckdb-sql-ctf/data/` (régénéré juste après).

### 4.3 — Terraform apply

```bash
set -a && source .env && set +a
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform apply -auto-approve -input=false
```

Souvent un no-op (les flags scénario 5/6/7 dans `locals.tf` sont génériques et ne changent pas), mais à lancer pour aligner l'état.

### 4.4 — Régénérer les données

```bash
cd data_generator && uv run ctf-generate generate-all --upload
```

Cela régénère scénarios 1, 2, 3 (PostgreSQL), 4, 5 et upload tout sur S3.

### 4.5 — Vérifier le flag scénario 3

```bash
aws s3 cp s3://duckdb-sql-ctf/leaderboard/answers/scenario_3.txt -
```

Doit afficher : `FLAG{https://jeremynadal33.github.io/duckdb-sql-ctf/le-canard-enchaine-<JJ-mois-AAAA>.md}` avec la nouvelle date.

### 4.6 — Sanity check end-to-end : `solve-all`

Faire jouer tous les solutionators à la chaîne — c'est le meilleur garde-fou avant de pusher. Si un scénario s'est cassé entre la modif des constantes et la régénération, ça apparaît ici.

```bash
cd data_generator && uv run ctf-generate solve-all
```

`solve-all` (cf. `data_generator/src/data_generator/entrypoint.py`) enchaîne les scénarios 1 → 6 en réutilisant le flag de chaque étape pour configurer la suivante (le flag scénario 1 contient les creds AWS utilisés pour les scénarios 2/4/5, le flag scénario 2 contient les creds PG utilisés pour 3/6). Chaque solver compare le flag récupéré au flag canonique et lève une `AssertionError` en cas de mismatch.

Sortie attendue : 6 lignes `[scenario N] Flag: FLAG{...}`. Si l'une échoue avec un mismatch ou une erreur de connexion :
- **scénario 3 mismatch** → le journal n'a pas le bon nom de fichier ou la date est désynchronisée vs `QUACKIE_DEATH_DATE`
- **scénario 4 mismatch** → la death date n'est pas comprise entre les snapshots Iceberg (rare, mais possible si on a touché à la logique snapshot)
- **scénario 6 mismatch** → coords Quackie qui ne reverse-geocodent pas vers la ville decoy attendue ; revoir lat/lon dans `constants.py`

Ne pas continuer vers le push tant que `solve-all` ne passe pas intégralement.

## Étape 5 — Validation + push

À ce stade tout est régénéré côté infra/S3, mais **GH Pages ne servira le nouveau journal qu'après push sur `main`**. Sans push, le flag scénario 3 mène à une 404.

1. Montrer à l'utilisateur :
   ```bash
   git status --short
   git diff --stat
   ```
2. Demander **explicitement** validation : "OK pour commit + push sur main ?"
3. Sur OK uniquement :
   ```bash
   git add data_generator/src/data_generator/constants.py docs/solutions.md docs/map/map.js docs/map/locations.js docs/agent.js docs/le-canard-enchaine-<JJ-mois-AAAA>.md
   git rm docs/le-canard-enchaine-<ancien>.md
   git commit -m "feat(ctf): prepare session du <JJ mois AAAA> à <ville>"
   git push origin main
   ```

   - Stager les fichiers **explicitement par chemin**, jamais `git add -A` ou `.` (le repo a souvent d'autres modifs en cours).
   - Format du commit : conventionnel (`feat(ctf): ...`), sujet < 70 chars, en français.
   - **Jamais** `--force` ou `--no-verify`.

## Garde-fous

- **Ne pas modifier** ces fichiers (stables d'une session à l'autre) :
  - Les noms d'institutions "du Lac" dans les générateurs (`scenario1_logs.py`, `scenario2_parquet.py`, `scenario3_postgres.py`, `scenario4_iceberg.py`, `scenario5_graph.py`).
  - Les emails `@bibliotheque-du-lac.fr`.
  - Les employeurs Bordeaux dans `EMPLOYERS_FR`.
  - `docs/scenarios/scenario-1.md`, `scenario-2.md`, `scenario-7.md`, `index.html`.
  - `docs/scenarios/scenario-4.md` (a un placeholder `<date avant la mort de Quackie Chan>` exprès).
  - `docs/dev-data/generate.py` (données de dev frontend, pas liées aux sessions).

- **Ne pas régénérer la stack from-scratch** : `terraform apply` (pas `destroy + apply`). Le bucket et la RDS persistent.

- **Ne pas pusher sans validation utilisateur explicite** — c'est l'invariant le plus important de ce skill.

## Si quelque chose tourne mal

- Tests qui échouent après modif `constants.py` → vérifier que les 5 blocs ont bien `_CITY`, `_LAT`, `_LON` (pas de typo). `DECOY_CITY = LIBRARY_CITY` est un alias, ne pas y toucher.
- `terraform apply` qui demande à recréer beaucoup de choses → STOP, c'est probablement un état désynchronisé. Ne pas appliquer.
- `generate-all` qui échoue sur `terraform output` → terraform output -json doit fonctionner ; relancer une fois suffit souvent (race condition rare).
- Flag scénario 3 qui contient l'ancien nom de fichier → le regenerator scénario 3 n'a pas tourné ; relancer `uv run ctf-generate postgres`.
