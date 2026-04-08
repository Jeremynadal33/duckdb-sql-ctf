# DuckDB SQL CTF — Opération Dossiers Disparus

## Prologue

Vous êtes enquêteur au sein du **C.A.C.** (unité spéciale d'investigation). Ce matin, une alerte a été remontée par la **Bibliothèque du Lac** : plusieurs documents officiels empruntés dans la journée d'hier n'ont pas été retournés avant la fermeture, comme l'exige le règlement. Parmi ces documents, un nombre anormalement élevé semble concerner un même type de document...

Votre mission : identifier les documents manquants, remonter la piste de l'emprunteur, découvrir son identité et comprendre ses motivations.

Chaque étape de l'enquête vous révèlera un **flag** au format `FLAG{...}` contenant les informations nécessaires pour accéder à l'étape suivante. Soumettez vos flags au fur et à mesure pour valider votre progression.

> **Pré-requis** : Installez [DuckDB](https://duckdb.org/docs/installation/) sur votre machine. Toutes les requêtes de ce CTF se font via DuckDB.

---

## Scenario 1 — Les Registres de la Bibliothèque

### Contexte

La Bibliothèque du Lac vous transmet une archive `library_logs.zip` contenant les registres de prêts de la journée. Chaque fichier `.json` contient une centaine d'enregistrements de prêts. Certains documents n'ont pas été retournés.

### Objectif

1. Charger l'ensemble des fichiers JSON dans DuckDB
2. Identifier les documents qui n'ont **pas été retournés** (pas de date de retour)
3. Parmi ceux-ci, déterminer quel **type de document** revient de façon suspecte
4. Extraire le flag caché dans les **métadonnées** des documents suspects

### Ce que vous cherchez

Le flag de ce scenario est constitué de fragments dissimulés dans les métadonnées des documents suspects. Une fois rassemblés et **ordonnés correctement**, ils forment : `FLAG{aws_access_key_id=...,aws_secret_access_key=...,bucket=...}`

Ces credentials vous donneront accès aux archives numériques pour le scenario suivant.

<details>
<summary>Indice 1 — Charger des fichiers JSON avec DuckDB</summary>

```sql
-- Lire tous les fichiers JSON d'un dossier
SELECT * FROM read_json_auto('chemin/vers/logs/*.json');
```

</details>

<details>
<summary>Indice 2 — Filtrer les documents non retournés</summary>

```sql
-- Les documents non retournés ont un champ timestamp_return à NULL
SELECT * FROM read_json_auto('logs/*.json')
WHERE timestamp_return IS NULL;
```

</details>

<details>
<summary>Indice 3 — Identifier le type de document suspect</summary>

```sql
-- Compter les documents non retournés par type
SELECT document_type, COUNT(*) as nb
FROM read_json_auto('logs/*.json')
WHERE timestamp_return IS NULL
GROUP BY document_type
ORDER BY nb DESC;
```

</details>

<details>
<summary>Indice 4 — Reconstituer le flag</summary>

```sql
-- Les fragments sont dans le champ metadata.notes des documents suspects
-- Pensez à l'ordre chronologique pour les remettre dans le bon sens...
SELECT metadata.notes, timestamp_checkout
FROM read_json_auto('logs/*.json')
WHERE timestamp_return IS NULL
  AND document_type = '???'
ORDER BY timestamp_checkout;
```

Concaténez les fragments dans cet ordre pour reconstituer le flag.

</details>

---

## Scenario 2 — Les Archives du Lac

### Contexte

Grâce aux credentials AWS obtenus au scenario précédent, vous avez maintenant accès à un bucket S3 contenant les archives numériques de la Bibliothèque du Lac. Plusieurs fichiers Parquet y sont stockés, représentant différentes tables de données. Un fichier `README.md` vous donne des indications sur leur contenu.

L'emprunteur a signé le registre à la main — son nom est approximatif et varie d'un prêt à l'autre. Vous devez retrouver son identité exacte dans l'annuaire des employés.

### Objectif

1. Configurer l'accès S3 dans DuckDB avec les credentials du flag précédent
2. Explorer les fichiers Parquet du bucket pour comprendre les données disponibles
3. Retrouver l'identité de l'emprunteur en croisant les noms approximatifs des registres avec l'annuaire des employés (correspondance floue)
4. Explorer les métadonnées des tables pour extraire le flag

### Ce que vous cherchez

Le flag de ce scenario contient les informations de connexion PostgreSQL : `FLAG{pg_host=...,pg_user=...,pg_password=...,pg_dbname=...}`

Il est caché dans les champs de métadonnées des tables — la plupart contiennent du bruit, mais certaines lignes sont intéressantes...

<details>
<summary>Indice 1 — Configurer l'accès S3 dans DuckDB</summary>

```sql
-- Installer et charger l'extension httpfs
INSTALL httpfs;
LOAD httpfs;

-- Configurer les credentials S3
CREATE SECRET my_s3_secret (
    TYPE S3,
    KEY_ID 'votre_access_key',
    SECRET 'votre_secret_key',
    REGION 'eu-west-1'
);
```

</details>

<details>
<summary>Indice 2 — Lire des fichiers Parquet depuis S3</summary>

```sql
-- Lister et lire les fichiers
SELECT * FROM read_parquet('s3://bucket-name/data/employees/*.parquet') LIMIT 10;
```

</details>

<details>
<summary>Indice 3 — Correspondance floue (fuzzy matching)</summary>

```sql
-- DuckDB dispose de fonctions de similarité de chaînes
-- jaro_winkler_similarity retourne un score entre 0 et 1
SELECT
    e.first_name || ' ' || e.last_name AS employee_name,
    jaro_winkler_similarity('nom_approximatif', e.first_name || ' ' || e.last_name) AS score
FROM read_parquet('s3://bucket/data/employees/*.parquet') e
ORDER BY score DESC
LIMIT 10;
```

</details>

<details>
<summary>Indice 4 — Fouiller les métadonnées</summary>

Chaque table possède un champ `metadata` au format JSON. La plupart des lignes contiennent du bruit aléatoire, mais les lignes correspondant à l'employé suspect contiennent quelque chose d'intéressant. Pensez à chercher dans **plusieurs tables**.

</details>

---

## Scenario 3 — L'Identité du Suspect

### Contexte

Vous avez identifié l'employé suspect et obtenu les accès à la base de données PostgreSQL de la Bibliothèque du Lac. Cette base contient des informations détaillées sur les personnes : état civil, profession et localisation.

L'enquête prend un tournant : les enquêteurs envoyés au domicile du suspect découvrent qu'il a été retrouvé sans vie — victime d'un accident de chasse. Quelqu'un de son entourage a dû utiliser son badge...

Il faut comprendre qui était cette personne et surtout, où se trouvent les gens qui l'entourent.

### Objectif

1. Se connecter à la base PostgreSQL depuis DuckDB
2. Retrouver les informations complètes du suspect (nom, profession, localisation)
3. Comprendre que le suspect est un médecin — son badge a pu être utilisé par quelqu'un de son entourage
4. Déterminer dans quelle ville vit le suspect grâce à ses coordonnées GPS
5. Consulter la table `city_information` pour trouver le flag

### Ce que vous cherchez

Le flag de ce scenario vous donnera accès aux données du graphe relationnel : `FLAG{...}`

<details>
<summary>Indice 1 — Se connecter à PostgreSQL depuis DuckDB</summary>

```sql
-- Installer et charger l'extension postgres
INSTALL postgres;
LOAD postgres;

-- Attacher la base de données
ATTACH 'host=... port=5432 dbname=... user=... password=...' AS ctfdb (TYPE POSTGRES);
```

</details>

<details>
<summary>Indice 2 — Explorer les tables disponibles</summary>

```sql
-- Lister les tables de la base
SHOW ALL TABLES;

-- Ou plus spécifiquement
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';
```

</details>

<details>
<summary>Indice 3 — Jointures entre tables</summary>

```sql
-- Croiser les informations personne / profession / adresse
SELECT p.first_name, p.last_name, pr.title, a.latitude, a.longitude
FROM ctfdb.persons p
JOIN ctfdb.professions pr ON pr.person_id = p.id
JOIN ctfdb.addresses a ON a.person_id = p.id
WHERE a.is_current = true;
```

</details>

<details>
<summary>Indice 4 — Géocodage inversé avec DuckDB</summary>

```sql
-- DuckDB peut faire des requêtes HTTP ! Utilisez l'API Nominatim pour
-- retrouver la ville à partir de coordonnées GPS
INSTALL httpfs;
LOAD httpfs;

WITH nominatim_request AS (
    SELECT http_get(
        'https://nominatim.openstreetmap.org/reverse',
        headers => MAP {
            'User-Agent': 'DuckDB-CTF/1.0',
            'Accept': 'application/json'
        },
        params => MAP {
            'format': 'geocodejson',
            'lat': '44.8416',
            'lon': '-0.5833',
            'layer': 'address'
        }
    ) AS response
)
SELECT
    json_extract_string(response->>'body', '$.address.city') AS city
FROM nominatim_request;
```

</details>

<details>
<summary>Indice 5 — Chercher dans city_information</summary>

Une fois la ville identifiée, regardez dans la table `city_information`. Le champ `metadata` de certaines villes contient des informations utiles...

</details>

---

## Scenario 4 — Le Réseau du Suspect

### Contexte

Le médecin est décédé, mais son badge a été utilisé. Qui dans son entourage aurait pu s'en servir ? Pour le découvrir, vous devez explorer le réseau de relations sociales et familiales autour du médecin.

En analysant les liens entre les individus, vous découvrirez un proche avec un profil... troublant.

### Objectif

1. Charger les données relationnelles et construire un graphe avec DuckPGQ
2. Explorer le réseau du médecin décédé
3. Identifier le proche le plus suspect dans son entourage
4. Découvrir la note associée à cette relation qui révèle le mobile du crime
5. Extraire le flag final

### Ce que vous cherchez

Le flag final : `FLAG{...}` — la conclusion de l'enquête.

<details>
<summary>Indice 1 — Activer DuckPGQ</summary>

```sql
-- Installer et charger l'extension
INSTALL duckpgq;
LOAD duckpgq;
```

</details>

<details>
<summary>Indice 2 — Créer un graphe à partir de tables relationnelles</summary>

```sql
-- Créer un property graph
CREATE PROPERTY GRAPH social_network
VERTEX TABLES (persons)
EDGE TABLES (
    relationships
    SOURCE KEY (person_id_1) REFERENCES persons (id)
    DESTINATION KEY (person_id_2) REFERENCES persons (id)
);
```

</details>

<details>
<summary>Indice 3 — Requêter le graphe</summary>

```sql
-- Trouver les voisins directs du suspect
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r:relationships]->(p2:persons)
    WHERE p1.last_name = '???'
    COLUMNS (p2.first_name, p2.last_name, r.relationship_type, r.notes)
);
```

</details>

---

## Epilogue

> *Les agents du C.A.C. se rendent à l'adresse identifiée. Ils trouvent le suspect, incapable de fuir : il ne pouvait pas se résoudre à abandonner les 12 petits qu'il venait de récupérer. Ils étaient trop mignons.*
>
> *Affaire classée. Dossier archivé au 2ème buisson du Lac de Bordeaux.*

---

## Soumission des flags

Pour valider votre progression, soumettez chaque flag au format Parquet :

<details>
<summary>Comment soumettre un flag</summary>

```sql
-- Créer et exporter votre réponse
COPY (
    SELECT 'votre_username' AS username, 'FLAG{...}' AS flag
) TO 's3://duckdb-sql-ctf/user-inputs/votre_username_scenario_N.parquet' (FORMAT PARQUET);
```

</details>
