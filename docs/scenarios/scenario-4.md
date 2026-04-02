---
numero: 4
label: Réseau
titre: Le Réseau du Suspect
techniques: DuckPGQ, PROPERTY GRAPH, GRAPH_TABLE, MATCH
flag: FLAG{...}
flag_label: FLAG FINAL
---

Le médecin est décédé, mais son badge a été utilisé. Qui dans son entourage aurait pu s'en servir ? Explorez le réseau de relations sociales et familiales — vous découvrirez un proche avec un profil troublant.

## Objectifs

1. Construire un **property graph** avec DuckPGQ
2. Explorer le réseau du médecin décédé
3. Identifier le proche le plus suspect
4. Trouver la note qui révèle le **mobile** du crime

## Indices

### Indice 1 — Activer DuckPGQ

```sql
INSTALL duckpgq FROM community;
LOAD duckpgq;
```

### Indice 2 — Créer un property graph

```sql
CREATE PROPERTY GRAPH social_network
VERTEX TABLES (persons)
EDGE TABLES (
    relationships
    SOURCE KEY (person_id_1) REFERENCES persons (id)
    DESTINATION KEY (person_id_2) REFERENCES persons (id)
);
```

### Indice 3 — Requêter le graphe

```sql
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r:relationships]->(p2:persons)
    WHERE p1.last_name = '???'
    COLUMNS (p2.first_name, p2.last_name, r.relationship_type, r.notes)
);
```

## Épilogue

*Les agents du C.A.C. se rendent à l'adresse identifiée. Ils trouvent le suspect, incapable de fuir : il ne pouvait pas se résoudre à abandonner les 12 petits qu'il venait de récupérer. Ils étaient trop mignons.*

*Affaire classée. Dossier archivé au 2ème buisson du Lac de Bordeaux.*
