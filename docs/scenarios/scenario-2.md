---
numero: 2
label: Archives
titre: Les Archives du Lac
techniques:
    - Explore S3 bucket : https://duckdb.org/docs/current/sql/functions/pattern_matching#glob-function-to-find-filenames
    - read_parquet : https://duckdb.org/docs/data/parquet/overview.html
    - jaro_winkler_similarity : https://duckdb.org/docs/current/sql/functions/text#jaro_winkler_similaritys1-s2-score_cutoff
---

Grâce aux credentials (*AWS*) du scénario précédent, vous accédez aux archives numériques (*bucket S3*). L'emprunteur, ce gros malin, a signé à la main à chaque emprunt — son nom varie d'un prêt à l'autre. Vous devez retrouver son identité exacte dans l'annuaire des employés.

## Objectifs

1. Configurer l'accès S3 dans DuckDB
2. Explorer les fichiers bucket
3. Retrouver l'identité via **fuzzy matching**

## Indices

### Indice 1 — Lire des fichiers Parquet depuis S3

```sql
SELECT * FROM read_parquet('s3://<path-to-table>/*.parquet') LIMIT 10;
```

### Indice 2 — Fuzzy matching

```sql
SELECT
    e.first_name || ' ' || e.last_name AS employee_name, n.borrower_name,
    jaro_winkler_similarity(n.borrower_name,
        e.first_name || ' ' || e.last_name) AS score
FROM read_parquet('s3://bucket-name/data/employees/*.parquet') e
CROSS JOIN (SELECT *
FROM read_json('chemin/vers/logs/*.json')
WHERE timestamp_return IS NULL
  AND document_type = '???') as n
WHERE score > 0.8
ORDER BY score DESC;
```

### Indice 3 — Fouiller les métadonnées

Chaque table a un champ `metadata` JSON. Cherchez dans plusieurs tables — les lignes de l'employé suspect sont intéressantes.
