-- ============================================================
-- Test DuckPGQ — Scénario 4 : Le Réseau du Suspect
-- Usage : duckdb < test_graph.sql
--         ou dans le shell interactif : .read test_graph.sql
-- ============================================================

INSTALL duckpgq FROM community;
LOAD duckpgq;

-- ── Données ──────────────────────────────────────────────────

CREATE OR REPLACE TABLE persons (
    id          INTEGER PRIMARY KEY,
    first_name  VARCHAR,
    last_name   VARCHAR,
    birth_date  DATE
);

INSERT INTO persons VALUES
    (1,  'Quackie',  'Chan',     '1985-06-15'),
    (2,  'Hugh',     'Quackman', '1955-03-22'),
    (3,  'Donna',    'Duck',     '1958-11-01'),
    (4,  'Donald',   'Quack',    '1980-04-12'),
    (5,  'Daffy',    'Waters',   '1990-07-30'),
    (6,  'Scrooge',  'McDuck',   '1920-01-01');

CREATE OR REPLACE TABLE relationships (
    id             INTEGER PRIMARY KEY,
    person_id_1    INTEGER,
    person_id_2    INTEGER,
    relationship_type VARCHAR,
    notes          VARCHAR
);

INSERT INTO relationships VALUES
    (1, 2, 1, 'parent',    'Père biologique'),
    (2, 3, 1, 'parent',    'Mère biologique'),
    (3, 1, 4, 'colleague', 'Même service médical'),
    (4, 1, 5, 'colleague', 'Travaillait ensemble'),
    (5, 2, 6, 'associate', 'A volé les canetons pour les revendre à Scrooge — mobile confirmé'),
    (6, 3, 4, 'family',    'Lien familial éloigné');

-- ── Property Graph ───────────────────────────────────────────

CREATE OR REPLACE PROPERTY GRAPH social_network
VERTEX TABLES (persons)
EDGE TABLES (
    relationships
    SOURCE KEY (person_id_1) REFERENCES persons (id)
    DESTINATION KEY (person_id_2) REFERENCES persons (id)
);

-- ── Requêtes ─────────────────────────────────────────────────

-- 1. Voisins directs de Quackie Chan
SELECT '--- Voisins directs de Quackie Chan ---' AS query;
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r:relationships]-(p2:persons)
    WHERE p1.last_name = 'Chan'
    COLUMNS (
        p1.first_name || ' ' || p1.last_name AS source,
        r.relationship_type                   AS relation,
        p2.first_name || ' ' || p2.last_name AS voisin,
        r.notes                               AS notes
    )
);

-- 2. Tous les chemins de longueur 2 depuis Quackie
SELECT '--- Chemins de longueur 2 depuis Quackie ---' AS query;
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r1:relationships]-(p2:persons)-[r2:relationships]-(p3:persons)
    WHERE p1.last_name = 'Chan'
      AND p1.id != p3.id
    COLUMNS (
        p1.first_name || ' ' || p1.last_name AS depart,
        p2.first_name || ' ' || p2.last_name AS intermediaire,
        p3.first_name || ' ' || p3.last_name AS arrivee,
        r2.notes                              AS notes_lien
    )
);

-- 3. Chercher la note qui révèle le mobile
SELECT '--- Recherche du mobile ---' AS query;
FROM GRAPH_TABLE (social_network
    MATCH (p1:persons)-[r:relationships]->(p2:persons)
    WHERE r.notes LIKE '%volé%' OR r.notes LIKE '%mobile%'
    COLUMNS (
        p1.first_name || ' ' || p1.last_name AS suspect,
        p2.first_name || ' ' || p2.last_name AS complice,
        r.notes                               AS mobile
    )
);
