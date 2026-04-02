---
numero: 3
label: Identité
titre: L'Identité du Suspect
techniques: postgres ext., ATTACH, JOIN, http_get, Nominatim
flag: FLAG{...}
flag_note: Ce flag donne accès aux données du graphe relationnel.
flag_label: FLAG ATTENDU
---

Vous avez identifié l'employé et obtenu les accès PostgreSQL. L'enquête prend un tournant : le suspect a été retrouvé sans vie — victime d'un accident de chasse. Quelqu'un de son entourage a dû utiliser son badge…

## Objectifs

1. Se connecter à PostgreSQL depuis DuckDB
2. Retrouver les informations complètes du suspect
3. Déterminer sa **ville** via géocodage inversé (Nominatim)
4. Consulter la table `city_information` pour le flag

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

### Indice 3 — Jointures personne / profession / adresse

```sql
SELECT p.first_name, p.last_name, pr.title, a.latitude, a.longitude
FROM ctfdb.persons p
JOIN ctfdb.professions pr ON pr.person_id = p.id
JOIN ctfdb.addresses a ON a.person_id = p.id
WHERE a.is_current = true;
```

### Indice 4 — Géocodage inversé avec Nominatim

```sql
INSTALL httpfs; LOAD httpfs;
WITH req AS (
    SELECT http_get(
        'https://nominatim.openstreetmap.org/reverse',
        headers => MAP { 'User-Agent': 'DuckDB-CTF/1.0', 'Accept': 'application/json' },
        params  => MAP { 'format': 'geocodejson', 'lat': '48.879', 'lon': '2.283' }
    ) AS response
)
SELECT json_extract_string(response->>'body', '$.address.city') AS city FROM req;
```

### Indice 5 — Chercher dans city_information

Une fois la ville identifiée, regardez le champ `metadata` de la table `city_information` — certaines entrées contiennent des informations utiles.
