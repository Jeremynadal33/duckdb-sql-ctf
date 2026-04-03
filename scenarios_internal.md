# DuckDB SQL CTF — Document Interne de Construction

## Configuration Générale

### Personnages

| Nom | Rôle | Notes |
|-----|------|-------|
| **Quackie Chan** | Frère de Hugh / médecin | Propriétaire du badge utilisé. Retrouvé mort (accident de chasse). |
| **Hugh Quackman** | Père / emprunteur suspect | A volé les actes de naissance de ses 12 enfants. Utilise le badge de son frère Quackie, signe le registre avec des variations du nom de Quackie Chan. |
| **Donna Duck** | Mère des 12 bébés | Partenaire de Hugh Quackman |
| Quack Norris | Figurant / bruit dans les données | Emprunteur normal |
| Quackamole | Figurant / bruit dans les données | Emprunteur normal |
| ~20 autres noms | Figurants | Noms à thème canard (Donald Quack, Quackatoa, Bill Quacksby, etc.) |

### Variations du nom de Quackie Chan (pour fuzzy matching)

Utilisées par Hugh Quackman dans les registres (Scenario 1) — il signe avec le nom de son frère pour brouiller les pistes :
- `Quackie Chan`
- `Quack C.`
- `Quacky Chan`
- `Quackie C.`
- `Quacky Chen`
- `Quackee Chan`

### Format des flags

Chaque flag est encapsulé dans `FLAG{...}`. Les flags des scenarios 1 à 3 contiennent les credentials pour le scenario suivant.

| Scenario | Flag | Contenu |
|----------|------|---------|
| 1 | `FLAG{aws_access_key_id=AKIA...,aws_secret_access_key=...,bucket=duckdb-sql-ctf}` | Credentials S3 temporaires (STS) |
| 2 | `FLAG{pg_host=<rds_endpoint>,pg_port=5432,pg_user=ctf_reader,pg_password=...,pg_dbname=ctfdb}` | Connexion PG read-only |
| 3 | `FLAG{...}` | Accès aux données du graphe (TBD) |
| 4 | `FLAG{canards_anti_criminels_mission_accomplie}` | Flag classique final |

### Suivi des participants

Les participants écrivent leurs flags dans S3 :
```
s3://duckdb-sql-ctf/user-inputs/<username>_scenario_<N>.parquet
```
Schema : `(username VARCHAR, flag VARCHAR)`

---

## Scenario 1 — Les Registres de la Bibliothèque

### Données à générer

**Format** : 500 fichiers JSON dans une archive `library_logs.zip`. Chaque fichier contient **100 enregistrements** (lignes). Total : **50 000 enregistrements de prêts**.

**Nom de fichier** : `log_<uuid>.json`

### Schema JSON (un enregistrement)

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_type": "acte_de_naissance",
  "document_title": "Acte de naissance — Lac de Bordeaux — 2024-03-15 — Mère: Donna Duck",
  "borrower_name": "Quackie Chan",
  "timestamp_checkout": "2024-11-15T09:23:00Z",
  "timestamp_return": null,
  "metadata": {
    "library_branch": "Bibliothèque Centrale du Lac",
    "notes": "aws_secret_access_key=wJalrXUt"
  }
}
```

> **Note** : Pas de `badge_id` dans les logs. Le badge n'apparaît que dans les tables employés (Scenario 2). Le lien entre les scénarios se fait uniquement par fuzzy matching sur le nom de l'emprunteur.

### Structure d'un fichier JSON

Chaque fichier est un **tableau JSON** de 100 objets :
```json
[
  { "log_id": "...", "document_type": "...", ... },
  { "log_id": "...", "document_type": "...", ... },
  ...
]
```

### Types de documents

| Type | Fréquence sur les 50 000 logs | Parmi les non-retournés (~30) |
|------|-------------------------------|-------------------------------|
| `acte_de_naissance` | ~6 000 | **12** (le signal fort) |
| `carte_identite` | ~10 000 | 4 |
| `permis_conduire` | ~8 000 | 3 |
| `acte_de_mariage` | ~7 000 | 4 |
| `certificat_medical` | ~9 000 | 3 |
| `diplome` | ~5 000 | 2 |
| `titre_de_propriete` | ~5 000 | 2 |

### Règles de génération

1. **49 970 logs normaux** : `timestamp_return` renseigné (même jour, quelques heures après checkout). Emprunteurs variés parmi ~20 noms de figurants.
2. **30 logs non retournés** : `timestamp_return = null`
   - **12 actes de naissance** : tous empruntés sous des variations du nom Quackie Chan (Hugh signe avec le nom de son frère).
   - **18 autres** : types variés, emprunteurs variés (bruit réaliste — des gens qui oublient de rendre des docs, ça arrive).
3. **Fragments du flag** : répartis dans les `metadata.notes` des 12 actes de naissance. **Pas de préfixe `fragment_N:`**. Les participants doivent **trier par `timestamp_checkout`** pour reconstituer le flag dans le bon ordre.
   ```
   Notes des 12 actes (triés par timestamp_checkout) :
   FLAG{aws_a
   ccess_key_
   id=AKIAXXXXXXX
   XXXXX,aws_
   secret_acc
   ess_key=wJ
   alrXUtnFEM
   I/K7MDENG/
   bPxRfiCYEX
   AMPLEKEY,b
   ucket=duck
   db-sql-ctf}
   ```
   Concaténation dans l'ordre chronologique = le flag complet.
4. **Titres des actes de naissance** : contiennent timestamp de naissance, lieu, nom de la mère (Donna Duck). Les 12 correspondent à 12 bébés différents nés le même jour.
5. **Les 12 actes suspects** doivent être répartis dans des fichiers JSON **différents** (pas tous dans le même fichier).

### Données des logs normaux

- `borrower_name` : pioché parmi les ~20 figurants
- `timestamp_checkout` : entre 08:00 et 17:00 le 2024-11-15
- `timestamp_return` : 1 à 6 heures après checkout
- `metadata.notes` : texte aléatoire ou vide ("RAS", "Document en bon état", "", etc.)

---

## Scenario 2 — Les Archives du Lac (S3 Parquet)

### Structure du bucket

```
s3://duckdb-sql-ctf/data/
├── README.md
├── employees/
│   ├── part_001.parquet
│   ├── part_002.parquet
│   └── ...
├── badges/
│   ├── part_001.parquet
│   ├── part_002.parquet
│   └── ...
└── departments/
    ├── part_001.parquet
    └── ...
```

### README.md du bucket

```markdown
# Archives numériques — Bibliothèque du Lac

## Tables disponibles

- `employees/` — Annuaire du personnel (fichiers fragmentés)
- `badges/` — Registre des badges d'accès (fichiers fragmentés)
- `departments/` — Liste des départements (fichiers fragmentés)

Chaque dossier contient plusieurs fichiers `.parquet`.
Chaque employé possède un badge unique. Les badges sont rattachés aux employés via `employee_id`.
```

### Schemas Parquet

#### employees/*.parquet (~150 lignes, réparties en plusieurs fichiers)

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INT | PK |
| `first_name` | VARCHAR | Prénom |
| `last_name` | VARCHAR | Nom |
| `department_id` | INT | FK vers departments |
| `hire_date` | DATE | Date d'embauche |
| `email` | VARCHAR | Email professionnel |
| `metadata` | JSON | Champ JSON — bruit aléatoire sauf pour la cible |

**Données clés** :
- Quackie Chan : `department_id` = département médical
- `metadata` de Quackie Chan : contient la première moitié du flag PG
  ```json
  {"info": "FLAG{pg_host=<rds_endpoint>,pg_port=5432,pg_user=ctf_reader"}
  ```
- Toutes les autres lignes : `metadata` contient du bruit aléatoire
  ```json
  {"info": "xK9mQ2vL8nR4wP1j"}
  ```

#### badges/*.parquet (~150 lignes, réparties en plusieurs fichiers)

| Colonne | Type | Description |
|---------|------|-------------|
| `badge_id` | VARCHAR | PK (ex: BADGE-0042) |
| `employee_id` | INT | FK vers employees |
| `issued_date` | DATE | Date d'émission |
| `status` | VARCHAR | active / **inactive** / revoked / expired |
| `metadata` | JSON | Champ JSON — bruit aléatoire sauf pour la cible |

**Données clés** :
- BADGE-0042 : `employee_id` pointe vers Quackie Chan, **`status = inactive`** (il est décédé)
- `metadata` du badge cible : contient la seconde moitié du flag PG
  ```json
  {"info": ",pg_password=...,pg_dbname=ctfdb}"}
  ```
- Toutes les autres lignes : `metadata` contient du bruit aléatoire
  ```json
  {"info": "aB3cD5eF7gH9iJ1k"}
  ```

**Reconstitution du flag** : concaténer `employees.metadata.info` + `badges.metadata.info` pour l'employé correspondant au nom trouvé par fuzzy matching au Scenario 1.

#### departments/*.parquet (~10 lignes, réparties en plusieurs fichiers)

| Colonne | Type | Description |
|---------|------|-------------|
| `dept_id` | INT | PK |
| `dept_name` | VARCHAR | Nom (ex: "Service Médical", "Administration", ...) |
| `building` | VARCHAR | Bâtiment |
| `floor` | INT | Étage |

### Approche de résolution attendue

1. Lire `README.md` pour comprendre la structure
2. Fuzzy matching : comparer les noms approximatifs du Scenario 1 (Quackie Chan, Quack C., etc.) avec `employees.first_name || ' ' || employees.last_name`
3. Identifier Quackie Chan comme le meilleur match → noter son `id`
4. Retrouver son badge dans `badges/*.parquet` via `employee_id` → constater que le badge est **inactive**
5. Extraire `metadata.info` de la ligne employee + `metadata.info` de la ligne badge → concaténer = flag complet

---

## Scenario 3 — L'Identité du Suspect (PostgreSQL)

### Schema de la base `ctfdb`

```sql
CREATE TABLE persons (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    badge_id VARCHAR(20)
);

CREATE TABLE professions (
    id SERIAL PRIMARY KEY,
    person_id INT NOT NULL REFERENCES persons(id),
    title VARCHAR(100) NOT NULL,
    employer VARCHAR(200),
    start_date DATE,
    end_date DATE  -- NULL = poste actuel
);

CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    person_id INT NOT NULL REFERENCES persons(id),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    is_current BOOLEAN DEFAULT true
);

CREATE TABLE city_information (
    id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    metadata JSON
);
```

### Volume de données

| Table | Lignes | Notes |
|-------|--------|-------|
| `persons` | ~450 | Personnes variées, incluant les personnages clés |
| `professions` | ~550 | Certains ont plusieurs professions (historique) |
| `addresses` | ~1000 | Adresses actuelles et anciennes, coordonnées GPS |
| `city_information` | ~50 | Villes de la région bordelaise et alentours |

### Données clés

**Quackie Chan** (le médecin décédé) :
- `persons` : `first_name = 'Quackie'`, `last_name = 'Chan'`, `badge_id = 'BADGE-0042'`
- `professions` : `title = 'Médecin généraliste'`, `employer = 'Clinique du Lac'`
- `addresses` : `latitude = 44.8378`, `longitude = -0.5792`, `is_current = true` (correspond à Bordeaux centre)

**Hugh Quackman** (le frère / vrai suspect) :
- `persons` : `first_name = 'Hugh'`, `last_name = 'Quackman'`
- `professions` : `title = 'Professeur de sport'`, `employer = 'Lycée du Lac'`
- `addresses` : `latitude = 48.879226`, `longitude = 2.283274`, `is_current = true` (correspond à Devoxx)

**Table `city_information`** :

| city_name | metadata |
|-----------|----------|
| Bordeaux | `{"info": "FLAG{graph_source=...,graph_access=...}"}` |
| Paris | `{"info": "en vrai c'est vraiment pas loin là, check ptet sur une carte"}` |
| Mérignac | `{"info": "rien à signaler"}` |
| Pessac | `{"info": "rien à voir ici"}` |
| ... | `{"info": "..."}` |

Le flag du Scenario 3 est dans le champ `metadata.info` de la ville correspondant à l'adresse du **médecin** (Quackie Chan → Bordeaux).

L'indice dans la ville de Hugh Quackman (Paris) devrait les pousser à chercher dans la pièce.

### Approche de résolution attendue

1. `ATTACH` la base PG depuis DuckDB
2. Chercher Quackie Chan dans `persons` (par nom, trouvé au Scenario 2)
3. `JOIN professions` → découvrir qu'il est médecin
4. `JOIN addresses` → récupérer ses coordonnées GPS (latitude, longitude)
5. Utiliser `http_get()` + API Nominatim pour faire du **géocodage inversé** → trouver le nom de la ville
6. `SELECT * FROM city_information WHERE city_name = '...'` → extraire le flag du champ `metadata`
7. (Bonus) Faire pareil pour d'autres personnes et découvrir l'indice de Bordeaux Lac
<details>
<summary> Requete exemple http get</summary>

```sql
WITH nominatim_request AS (
    SELECT http_get(
      'https://nominatim.openstreetmap.org/reverse',
      headers => MAP {                                                                                                                                                                                                                              
        'User-Agent': 'DuckDB-Demo/1.0',
        'Accept': 'application/json'                                                                                                                                                                                                                
      },          
      params => MAP {
        'format': 'geocodejson',
        'lat': '48.879226',                                                                                                                                                                                                                      
        'lon': '2.283274',
        'layer': 'address'                                                                                                                                                                                                                          
      }           
    ) AS response
  )
  SELECT
    (response->>'status')::INT AS status,
    json_extract_string(response->>'body', '$.features[0].properties.geocoding.label') AS address,                                                                                                                                                  
    json_extract_string(response->>'body', '$.features[0].properties.geocoding.city') AS city,
    json_extract_string(response->>'body', '$.features[0].properties.geocoding.country') AS country                                                                                                                                                 
  FROM nominatim_request;
```

</details>

### User PostgreSQL pour les participants

Créer un user read-only dédié au CTF :
```sql
CREATE USER ctf_reader WITH PASSWORD '...';
GRANT CONNECT ON DATABASE ctfdb TO ctf_reader;
GRANT USAGE ON SCHEMA public TO ctf_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ctf_reader;
```

---

## Scenario 4 — Le Réseau du Suspect (DuckPGQ)

### Objectif technique

Les participants utilisent DuckPGQ pour modéliser les relations comme un graphe et explorer le réseau social autour du médecin décédé et de Quackie Chan.

### Données du graphe

**Source** : À déterminer (table PG `relationships` à créer, OU export en parquet).

**Noeuds** : table `persons` (id, first_name, last_name)
**Arêtes** : table `relationships` (person_id_1, person_id_2, relationship_type, notes)

> **Note** : La table `relationships` n'est PAS dans le schema PG du Scenario 3. Elle sera ajoutée/fournie spécifiquement pour le Scenario 4 (source à déterminer).

### Relations clés à découvrir

```
Hugh Quackman --[sibling]--> Quackie Chan (médecin, décédé)
Hugh Quackman --[partner]--> Donna Duck (mère des 12 bébés)
Hugh Quackman --[partner]--> ... (ex-partenaires, avec notes révélatrices)
Quackie Chan --[colleague]--> ... (autres médecins)
Donna Duck --[friend]--> ... (réseau social)
```

La note `"ne garde jamais une partenaire très longtemps"` est sur une des relations `partner` passées de Hugh Quackman, écrite par un tiers (un ami ou collègue).

### Flag final

`FLAG{canards_anti_criminels_mission_accomplie}`

Caché dans : le champ `notes` de la relation entre Hugh Quackman et Donna Duck, ou accessible uniquement via une requête de traversée de graphe (shortest path entre deux personnes spécifiques).

### Approche de résolution attendue

1. Charger l'extension DuckPGQ
2. Créer un `PROPERTY GRAPH` à partir des tables persons/relationships
3. Explorer les voisins de Quackie Chan → trouver Hugh Quackman
4. Explorer les relations de Hugh Quackman → trouver Donna Duck + la note sur les partenaires
5. Extraire le flag final

---

## Checklist de construction

- [ ] Écrire le générateur de JSON logs (Scenario 1) dans `data_generator/`
  - [ ] 500 fichiers × 100 lignes, pas de badge_id, pas de fragment_N
  - [ ] 12 actes de naissance non retournés avec flag fragments ordonnés par timestamp
  - [ ] 18 autres non-retournés (bruit)
  - [ ] 49 970 logs normaux
- [ ] Générer et compresser `library_logs.zip`
- [ ] Générer les fichiers Parquet (Scenario 2) et les uploader sur S3
  - [ ] employees/*.parquet avec metadata JSON (flag part 1 pour Quackie Chan, fichiers fragmentés)
  - [ ] badges/*.parquet avec metadata JSON (flag part 2 pour BADGE-0042, status=inactive, fichiers fragmentés)
  - [ ] departments/*.parquet (fichiers fragmentés)
- [ ] Écrire le `README.md` du bucket S3
- [ ] Créer les tables PostgreSQL et insérer les données (Scenario 3)
  - [ ] persons (450 lignes)
  - [ ] professions (~550 lignes)
  - [ ] addresses (1000 lignes, lat/lon)
  - [ ] city_information (~50 villes avec metadata)
- [ ] Créer le user `ctf_reader` read-only sur RDS
- [ ] Définir la source de données du graphe (Scenario 4) — TBD
- [ ] Définir les valeurs exactes des flags (credentials réels)
- [ ] Tester le parcours complet de bout en bout
- [ ] Préparer le mécanisme de soumission des flags (lecture du bucket `user-inputs/`)
