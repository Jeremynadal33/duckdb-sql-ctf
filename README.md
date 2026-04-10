# Operation Dossiers Disparus — DuckDB SQL CTF

Un CTF (Capture The Flag) pour decouvrir DuckDB en apprenant a interroger plusieurs moteurs de bases de donnees (JSON, Parquet, PostgreSQL, Iceberg).

## Jouer au CTF

Le CTF est accessible directement via la GitHub Page :

**https://jeremynadal33.github.io/duckdb-sql-ctf/**


## Pre-requis

- Un navigateur web moderne (Chrome, Firefox, Safari, Edge)
- [DuckDB CLI](https://duckdb.org/install/) — necessaire pour certains scenarios

```bash
# Installation rapide
curl https://install.duckdb.org | sh
```

Lancer depuis votre terminal :
```bash
duckdb -ui
```

## Comment ca marche

1. Rendez-vous sur la [GitHub Page](https://jeremynadal33.github.io/duckdb-sql-ctf/)
2. Choisissez un scenario dans la section **Scenarios**
3. Lisez le briefing et les indices
4. Ecrivez vos requetes SQL avec DuckDB pour trouver les **flags**
5. Soumettez vos flags pour être tout en haut du **leaderboard**

## Developpement

```bash
# Lancer un serveur local pour le frontend
cd docs && python -m http.server 8000
```
