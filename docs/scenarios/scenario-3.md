---
numero: 3
label: Identité
titre: L'Identité du Suspect
techniques:
    - postgres extension : https://duckdb.org/docs/extensions/postgres.html
    - ATTACH : https://duckdb.org/docs/sql/statements/attach.html
    - http_client : https://duckdb.org/community_extensions/extensions/http_client
    - Nominatim : https://nominatim.org/release-docs/latest/api/Reverse/
---

L'identité de l'employé est confirmée. Grâce aux accréditations récupérées, vous accédez désormais aux registres nationaux (*base PostgreSQL*) contenant coordonnées et historique d'adresses. Localisez le suspect avant qu'il ne disparaisse.

## Objectifs

1. Se connecter à PostgreSQL depuis DuckDB
2. Retrouver les informations complètes du suspect
3. Déterminer sa **ville** via géocodage inversé (Nominatim).

## Indices

### Indice 1 — Se connecter à PostgreSQL

```sql
INSTALL postgres; LOAD postgres;
ATTACH 'host=... port=5432 dbname=... user=... password=...'
    AS ctfdb (TYPE POSTGRES);
```

### Indice 2 — Explorer les tables

```sql
SHOW ALL TABLES;
```

### Indice 3 — Jointures personne / adresse

```sql
SELECT p.first_name, p.last_name, a.latitude, a.longitude
FROM ctfdb.persons p
JOIN ctfdb.addresses a ON a.person_id = p.id
WHERE a.is_current = true;
```

### Indice 4 — Géocodage inversé avec Nominatim

```sql
INSTALL http_client FROM community; LOAD http_client;
WITH req AS (
    SELECT http_get(
        'https://nominatim.openstreetmap.org/reverse',
        headers => MAP { 'User-Agent': 'DuckDB-CTF/1.0', 'Accept': 'application/json' },
        params  => MAP { 'format': 'geocodejson', 'lat': '35.6764', 'lon': '139.6500' }
    ) AS response
)
SELECT response, json_extract_string(response->>'body', '$') AS city FROM req;
```

### Indice 5 — Chercher des informations sur la ville

Une fois la ville identifiée, regardez le champ `metadata` de la table `city_information` — certaines entrées contiennent des informations utiles.
