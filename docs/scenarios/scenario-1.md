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
4. Trouver et recomposer le flag, il vous donnera les creds AWS nécessaire pour la suite de l'enquête
5. Utiliser le global helper afin de soumettre votre premier le flag ! 

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
* Utiliser une [CTE](https://learnsql.com/blog/what-is-common-table-expression/) afin d'extraire le champ souhaité et d'ordonner les documents
* Ensuite, utiliser les fonctions [array_agg](https://duckdb.org/docs/current/sql/functions/aggregates#listarg) 
* Enfin, utiliser [array_to_string](https://duckdb.org/docs/current/sql/functions/list#array_to_stringlist-delimiter) afin de facilement afficher le résultat

### Indice 4 — Solution

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
