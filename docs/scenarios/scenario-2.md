---
numero: 2
label: Archives
titre: Les Archives du Lac
techniques: httpfs, read_parquet, CREATE SECRET, jaro_winkler_similarity
flag: FLAG{pg_host=...,pg_user=...,pg_password=...,pg_dbname=...}
flag_note: Ces credentials donnent accès à la base PostgreSQL pour le scénario suivant.
flag_label: FLAG ATTENDU
---

Grâce aux credentials AWS du scénario précédent, vous accédez à un bucket S3 contenant les archives numériques. L'emprunteur a signé à la main — son nom varie d'un prêt à l'autre. Vous devez retrouver son identité exacte dans l'annuaire des employés.

## Objectifs

1. Configurer l'accès S3 dans DuckDB
2. Explorer les fichiers Parquet du bucket
3. Retrouver l'identité via **correspondance floue**
4. Explorer les **métadonnées** des tables pour extraire le flag

## Indices

### Indice 1 — Configurer l'accès S3

```sql
INSTALL httpfs; LOAD httpfs;

CREATE SECRET my_s3_secret (
    TYPE S3,
    KEY_ID 'votre_access_key',
    SECRET 'votre_secret_key',
    REGION 'eu-west-1'
);
```

### Indice 2 — Lire des fichiers Parquet depuis S3

```sql
SELECT * FROM read_parquet('s3://bucket-name/data/employees.parquet') LIMIT 10;
```

### Indice 3 — Correspondance floue

```sql
SELECT
    e.first_name || ' ' || e.last_name AS employee_name,
    jaro_winkler_similarity('nom_approximatif',
        e.first_name || ' ' || e.last_name) AS score
FROM read_parquet('s3://bucket/data/employees.parquet') e
ORDER BY score DESC LIMIT 10;
```

### Indice 4 — Fouiller les métadonnées

Chaque table a un champ `metadata` JSON. Cherchez dans plusieurs tables — les lignes de l'employé suspect sont intéressantes.
