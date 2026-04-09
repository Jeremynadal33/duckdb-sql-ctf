---
numero: 1
label: Registres
titre: Les Registres de la Bibliothèque
techniques:
    - read_json : https://duckdb.org/docs/data/json/overview.html
    - httpfs : https://duckdb.org/docs/extensions/httpfs/overview.html
    - CREATE SECRET : https://duckdb.org/docs/current/configuration/secrets_manager#temporary-secrets

---

La Bibliothèque du Lac vous transmet une archive [`library_logs.zip`](https://duckdb-sql-ctf.s3.eu-west-1.amazonaws.com/data/library_logs.zip) contenant les registres de prêts de la journée. Certains documents n'ont pas été retournés.

## Objectifs

1. Charger l'ensemble des fichiers JSON dans DuckDB
2. Identifier les documents qui n'ont **pas été retournés**
3. Déterminer quel **type de document** revient de façon suspecte

## Indices

### Indice 1 — Charger des fichiers JSON

```sql
SELECT * FROM read_json('chemin/vers/logs/*.json');
```

### Indice 2 — Identifier le type suspect

```sql
SELECT document_type, COUNT(*) AS nb
FROM read_json('logs/*.json')
WHERE timestamp_return IS NULL
GROUP BY document_type
ORDER BY nb DESC;
```

### Indice 3 — Reconstituer le flag

```sql
with data as (
  select
    metadata.notes as flag_part
  from
    read_json('logs/*.json')
  where
    timestamp_return is null
    and document_type = '???'
  order by
    timestamp_checkout asc
)

select
  array_to_string(array_agg(flag_part), '') as flag
from
  data
```


Concaténez les fragments dans l'ordre chronologique.
