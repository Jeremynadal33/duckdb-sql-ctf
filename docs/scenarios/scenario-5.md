---
numero: 5
label: Réseau
titre: Le Réseau du Suspect
techniques:
    - ATTACH : https://duckdb.org/docs/sql/statements/attach.html
    - Visualiseur graphe : ../graph/
    - DuckPGQ : https://duckdb.org/community_extensions/extensions/duckpgq
    - PROPERTY GRAPH : https://duckdb.org/docs/current/guides/sql_features/graph_queries#creating-a-property-graph
    - MATCH : https://duckdb.org/docs/current/guides/sql_features/graph_queries#pattern-matching
---

Le médecin est décédé, son badge a été usurpé. Mais qui pouvait y avoir accès dans son entourage ?
Les métadonnées récupérées pointent vers une base de données du réseau social de la bibliothèque. Cartographiez les relations autour de Quackie Chan : l'un de ses proches a un profil particulièrement troublant.

&nbsp; 

Deux approches s'offrent à vous : explorer le graphe visuellement via le [visualiseur graphique](../graph/), ou utiliser l'extension DuckPGQ en "SQL".

## Objectifs

1. Charger la base du réseau de **Quackie Chan**
2. Si **Chemin B** : Construire un graph à partir des tables `persons` et `relationships` à l'aide de DuckDBPGQ
3. Parcourir le graph et identifier le proche suspect afin de trouver le flag

## Indices

### Chemin A - Indice 1 : Le visualiseur de graphe

Ouvrez le [visualiseur de graphe](../graph/) intégré au site. Deux options pour charger les données :

- **Depuis S3** : collez le chemin `s3://bucket/data/network.duckdb` dans le champ S3 et cliquez *Charger*
- **Fichier local** : téléchargez le fichier `.duckdb` et importez-le via le bouton *Fichier .duckdb*

### Chemin A - Indice 2 : Les proches de Quackie Chan

Une fois le graphe affiché :

1. Cherchez **Quackie Chan** via le champ de recherche
2. **Double-cliquez** sur le nœud pour isoler son voisinage

### Chemin A - Indice 3 : Ou chercher

1. Repérez le chemin en 2 sauts : Quackie → Soeur → Conjoint
5. Le flag apparaît dans le champ **Notes** (surligné en vert)



### Chemin B - Indice 1 : Télécharger la base depuis S3

```bash
curl -O https://duckdb-sql-ctf.s3.eu-west-1.amazonaws.com/data/network.duckdb
```

### Chemin B - Indice 2 : Explorer les tables

```sql
ATTACH '<path>/network.duckdb' AS social (READ_ONLY);
SELECT * FROM social.persons LIMIT 10;
SELECT * FROM social.relationships LIMIT 10;
```

### Chemin B - Indice 3 : Création du graph avec DuckPGQ (SQL)

> **Attention :** l'extension communautaire DuckPGQ nécessite DuckDB **< 1.5.0**. Si vous utilisez une version plus récente, privilégiez le Chemin A (visualiseur) ci-dessus.

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

### Chelin B - Indice 4 : Traverser le graphe depuis Quackie Chan

> Cet indice concerne le Chemin B (DuckPGQ). Si vous utilisez le visualiseur, l'indice 3a suffit.

Le suspect n'a pas de lien direct avec Quackie — il faut traverser un intermédiaire.

```sql
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r1:relationships]->(p2:persons)-[r2:relationships]->(p3:persons)
    WHERE p1.first_name = 'Quackie' AND p1.last_name = 'Chan'
    COLUMNS (p2.first_name AS inter_prenom, p2.last_name AS inter_nom,
             r1.relationship_type AS lien_1,
             p3.first_name AS suspect_prenom, p3.last_name AS suspect_nom,
             p3.occupation, r2.relationship_type AS lien_2, r2.notes)
);
```

Le flag se trouve dans la colonne `notes` de la relation avec le proche au profil suspect.



