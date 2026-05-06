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
2. Le bucket contient un dossier `data` dans lequel se trouve un `README.md`. Allez y jeter un oeil !
3. Retrouver l'identité via **fuzzy matching**

## Indices

### Indice 1 — Explorer le README.md
```sql
COPY (
    SELECT content
    FROM read_text('s3://duckdb-sql-ctf/data/README.md')
) TO '~/Desktop/fichier.md' (FORMAT CSV, HEADER false, QUOTE '', DELIMITER E'\x01');
```

### Indice 2 — Lire des fichiers Parquet depuis S3

```sql
SELECT * FROM read_parquet('s3://<path-to-table>/*.parquet') LIMIT 10;
```

### Indice 3 — Fuzzy matching

```sql
-- Get borrower's modified ids
with identities as (
  select
    'J. Nadal' as borrower_name
  union all
  select
    'P. Farey' as borrower_name
  union all
  select
    'Jeremy Nadal' as borrower_name
  union all
  select
    'Jeremy N' as borrower_name
)

, employees as (
  select
    'Jérémy Nadal' as employee_name
  union
  select
    'Pablo Farey' as employee_name
  
)

, similar_employees as (
  select
    jaro_winkler_similarity(i.borrower_name, e.employee_name) AS score
    , i.borrower_name
    , e.employee_name
  from
    employees as e
  cross join
    identities as i
  where
    score > 0.8
)

select
  distinct
  *
from
  similar_employees
```

### Indice 4 — Fouiller les métadonnées

Chaque table a un champ `metadata` JSON... Des informations intéressantes peuvent s'y cacher.
