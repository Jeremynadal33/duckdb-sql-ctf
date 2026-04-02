---
numero: 1
label: Registres
titre: Les Registres de la Bibliothèque
techniques: read_json_auto, IS NULL, GROUP BY, ORDER BY
flag: FLAG{aws_access_key_id=...,aws_secret_access_key=...,bucket=...}
flag_note: Ces credentials donnent accès aux archives S3 pour le scénario suivant.
flag_label: FLAG ATTENDU
---

La Bibliothèque du Lac vous transmet une archive `library_logs.zip` contenant les registres de prêts de la journée. Chaque fichier `.json` contient une centaine d'enregistrements. Certains documents n'ont pas été retournés.

## Objectifs

1. Charger l'ensemble des fichiers JSON dans DuckDB
2. Identifier les documents qui n'ont **pas été retournés**
3. Déterminer quel **type de document** revient de façon suspecte
4. Extraire le flag caché dans les **métadonnées** des documents suspects

## Indices

### Indice 1 — Charger des fichiers JSON

```sql
SELECT * FROM read_json_auto('chemin/vers/logs/*.json');
```

### Indice 2 — Filtrer les documents non retournés

```sql
SELECT * FROM read_json_auto('logs/*.json')
WHERE timestamp_return IS NULL;
```

### Indice 3 — Identifier le type suspect

```sql
SELECT document_type, COUNT(*) AS nb
FROM read_json_auto('logs/*.json')
WHERE timestamp_return IS NULL
GROUP BY document_type
ORDER BY nb DESC;
```

### Indice 4 — Reconstituer le flag

```sql
SELECT metadata.notes, timestamp_checkout
FROM read_json_auto('logs/*.json')
WHERE timestamp_return IS NULL
  AND document_type = '???'
ORDER BY timestamp_checkout;
```

Concaténez les fragments dans l'ordre chronologique.
