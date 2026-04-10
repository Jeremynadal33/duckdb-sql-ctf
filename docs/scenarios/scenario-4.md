---
numero: 4
label: Voyage
titre: Le Voyage dans le Temps
techniques:
    - iceberg ext. : https://duckdb.org/docs/current/core_extensions/iceberg/overview
    - TIME TRAVEL
    - iceberg_snapshots : https://duckdb.org/docs/current/core_extensions/iceberg/overview#visualizing-snapshots
---

Vous vous rendez à l'adresse de Quackie Chan. L'endroit est désert — personne ne semble y être passé depuis un moment. Sur la table, pourtant, vous trouvez un article du *Canard Enchaîné* daté du mois dernier. Le médecin est décédé. Son badge a pourtant continué d'être utilisé après sa mort… Mais par qui ?

Les badges d'accès sont stockés sur les archives numériques (*S3*) au format **Apache Iceberg**, un format de table qui conserve l'historique complet des modifications. Remontez dans le temps pour retrouver les métadonnées originales du badge de Quackie.

## Objectifs

1. Installer l'extension Iceberg dans DuckDB
2. Explorer la table `badges/` dans les archives
3. Lister les **snapshots** disponibles et repérer les dates
4. Retrouver le snapshot qui contient le flag

## Indices

### Indice 1 — Installer l'extension Iceberg

```sql
INSTALL iceberg; LOAD iceberg;
```

### Indice 2 - Configurer l'extension pour des tables sans indices de versions
```sql
SET unsafe_enable_version_guessing = true;
```

### Indice 2 — Scanner la table (dernier snapshot)

```sql
SELECT * FROM iceberg_scan('s3://bucket/data/badges/'
, allow_moved_paths = true);
```

Vous remarquerez que le badge de Quackie est **inactive** — les métadonnées ne contiennent rien d'utile dans l'état actuel.

### Indice 3 — Lister les snapshots

```sql
SELECT * FROM iceberg_snapshots('s3://bucket/data/badges/');
```

Comparez les dates des snapshots avec la date du décès mentionnée dans l'article du Canard Enchaîné.

### Indice 4 — Voyager dans le temps

```sql
SELECT * FROM iceberg_scan(
    's3://bucket/data/badges/',
    snapshot_from_timestamp => TIMESTAMP '2026-03-01',
    allow_moved_paths = true
)
WHERE badge_id = 'BADGE-0042';
```

Choisissez une date **avant le décès** pour retrouver l'état du badge quand Quackie était encore en vie.
