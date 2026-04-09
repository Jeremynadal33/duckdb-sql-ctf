---
numero: 5
label: Réseau
titre: Le Réseau du Suspect
techniques:
    - ATTACH : https://duckdb.org/docs/sql/statements/attach.html
    - DuckPGQ : https://duckdb.org/community_extensions/extensions/duckpgq
    - PROPERTY GRAPH : https://duckdb.org/docs/current/guides/sql_features/graph_queries#creating-a-property-graph
    - MATCH : https://duckdb.org/docs/current/guides/sql_features/graph_queries#pattern-matching
---

Le médecin est décédé, son badge a été usurpé. Mais qui pouvait y avoir accès dans son entourage ?
Les métadonnées récupérées pointent vers une base de données du réseau social de la bibliothèque. Cartographiez les relations autour de Quackie Chan : l'un de ses proches a un profil particulièrement troublant.

## Objectifs

1. Charger la base du réseau (*DuckDB*) depuis les archives (*S3*)
2. Explorer les tables `persons` et `relationships`
3. Construire un **property graph** avec DuckPGQ
4. Traverser le graphe depuis Quackie Chan
5. Identifier le proche suspect et récupérer le flag dans la colonne `notes`

## Indices

### Indice 1 — Charger la base depuis S3

```sql
ATTACH 's3://bucket/data/network.duckdb' AS social (READ_ONLY);
SHOW ALL TABLES;
```

### Indice 2 — Explorer les tables

```sql
SELECT * FROM social.persons LIMIT 10;
SELECT * FROM social.relationships LIMIT 10;
```

### Indice 3 — Activer DuckPGQ et créer le graphe

```sql
INSTALL duckpgq FROM community;
LOAD duckpgq;

CREATE OR REPLACE PROPERTY GRAPH social_network
VERTEX TABLES (social.persons)
EDGE TABLES (
    social.relationships
        SOURCE KEY (person_id_1) REFERENCES social.persons (id)
        DESTINATION KEY (person_id_2) REFERENCES social.persons (id)
);
```

### Indice 4 — Traverser le graphe depuis Quackie Chan

```sql
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r:relationships]->(p2:persons)
    WHERE p1.first_name = 'Quackie' AND p1.last_name = 'Chan'
    COLUMNS (p2.first_name, p2.last_name, p2.occupation, r.relationship_type, r.notes)
);
```

Le flag se trouve dans la colonne `notes` de la relation avec le proche au profil suspect.

## Épilogue

*Les agents du C.A.C. se rendent à l'adresse identifiée. Ils trouvent le suspect, incapable de fuir : il ne pouvait pas se résoudre à abandonner les 12 petits qu'il venait de récupérer. Ils étaient trop mignons.*

*Affaire classée. Dossier archivé au 2ème buisson du Lac de Bordeaux.*
