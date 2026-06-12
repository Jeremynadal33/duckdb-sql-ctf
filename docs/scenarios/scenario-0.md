---
numero: 0
label: Tutoriel
titre: Tutoriel — Prise en main
techniques:
    - read_csv : https://duckdb.org/docs/data/csv/overview.html
    - COPY TO : https://duckdb.org/docs/sql/statements/copy
    - httpfs : https://duckdb.org/docs/extensions/httpfs/overview.html

---

Échauffons-nous ensemble sur la boucle du CTF (ce tutoriel ne rapporte aucun point) :

<div class="ctf-loop">
  <span class="ctf-loop-step">📖 Lire la donnée</span>
  <span class="ctf-loop-arrow">→</span>
  <span class="ctf-loop-step">🔎 Trouver le flag</span>
  <span class="ctf-loop-arrow">→</span>
  <span class="ctf-loop-step">📤 Soumettre un Parquet</span>
</div>

**1. Charger l'extension réseau**
```sql
INSTALL httpfs; LOAD httpfs;
```

**2. Lire le CSV public des bâtiments**
```sql
SELECT * FROM read_csv('https://duckdb-sql-ctf.s3.eu-west-1.amazonaws.com/data/buildings.csv');
```

**3. Trouver la bibliothèque — son champ `message` est le flag**
```sql
SELECT message
FROM read_csv('https://duckdb-sql-ctf.s3.eu-west-1.amazonaws.com/data/buildings.csv')
WHERE type = 'bibliothèque';
```

**4. S'entraîner à écrire le Parquet en LOCAL** (rien n'est envoyé)
```sql
COPY (
    SELECT '<pseudo>' AS pseudo, 0 AS scenario, 'FLAG{que le meilleur canard gagne}' AS flag
) TO 'ma_soumission.parquet' (FORMAT PARQUET);
```

**5. Dans les vrais scénarios** — écrire dans le bucket distant `user-inputs/`, ce qui exige des credentials AWS (la récompense du scénario 1)
```sql
CREATE OR REPLACE SECRET my_s3_secret (
    TYPE S3, KEY_ID '<key>', SECRET '<secret>', REGION 'eu-west-1'
);

COPY (
    SELECT '<pseudo>' AS pseudo, <N> AS scenario, 'FLAG{...}' AS flag
) TO 's3://<bucket>/user-inputs/<pseudo>_scenario_<N>.parquet' (FORMAT PARQUET);
```

Cette requête de soumission est toujours disponible dans le bouton <a href="#" onclick="openSubmitHelper(); return false;"><strong>GLOBAL HELPERS</strong></a>, en haut à droite de la page.
