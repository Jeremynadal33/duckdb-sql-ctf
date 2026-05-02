# TODO

## Data Generation
* Ajouter des fake flags pour tromper les joueurs (misleading rows)
* Points negatifs sur les faux flags pour eviter le brute force

## Slides (quasi fini)
* Kesako DuckDB
* Parler de WASM
* Parler de Mother Duck
* Disclaimer : on est pas des pros de DuckDB ou Iceberg
* REX Orange dbt-duckdb (mettre en bleu)
* REX VPC Flos : logs ingestion Snowflake -> couts d'ingestion 800k/an (Okta) https://www.youtube.com/watch?v=TrmJilG4GXk
* Conf Maxence
* Article : gerer > 1 To avec DuckDB https://blog.dataexpert.io/p/i-processed-1-tb-with-duckdb-in-30

## Scenarios
* Finir les scenarios a fournir aux joueurs
* Scenario 1 : ajouter une etape de reconstitution du flag
* Scenario 1 : afficher les global helpers directement dans le scenario (meme si mentionne a l'oral)
* Scenario 2 : rendre l'indice 1 plus evident
* Scenario 7 : corriger la typo "mision" -> "mission"
* Lat/long to city : mettre nom de l'API a dispo + http_get
* Indice lat/long : donne la reponse finale directement -> soit rendre random, soit supprimer (probleme de parsing)
* Rappeler le nom du personnage une fois trouve
* Modifier indice PG => utiliser secret !!
* Gérer le pb de sessions limites


## UX / Frontend
* Ajouter un logo canard sur l'onglet (favicon)
* Lag au chargement de la page -> les gens spam refresh
* Leaderboard : rendre scrollable pour petits ecrans (scenario 7 non visible) (pas sur au final, je pense que c'est juste parce que personne ne l'avait fait)
* Dire de faire `duckdb -ui`

## Auth / Utilisateurs
* Ajouter un user admin pour acceder a tous les scenarios
* Ajouter la possibilite de se deconnecter/reconnecter
* Lambda : preciser que le pseudo est case insensitive

## Anti-triche / Difficulte
* Mettre un timer sur l'ouverture des indices ? 

## Bugs
* Erreur sur le scenario Iceberg (critique)

## Questions ouvertes
* Faut-il ajouter des flags fictifs ? (ex: Azis qui voit d'autres flags) -> pas forcement necessaire

---

# Retours

## Alex N.
Scenario 1 et 2 faits sans indice. Le scenario 1 manque d'accompagnement : expliciter que le flag contient les creds AWS, afficher les global helpers directement. A partir du scenario 2, c'est autonome.

## MohClaude (Claude en full auto, 15 min sans indices)
Points positifs :
* Chaine progressive : chaque flag deverrouille le scenario suivant (AWS creds -> PostgreSQL -> S3 -> etc.)
* Showcase DuckDB complet : JSON, S3/httpfs, PostgreSQL attach, Iceberg time-travel, DuckPGQ, Nominatim HTTP
* Storytelling et jeux de mots canard (Quackie Chan, Hugh Quackman, "papa poule", "coin coin")
* Techniques de dissimulation : fragments dans metadata ordonnees par "Bebe #N", anomalie de longueur metadata sur 1 employe / 150, flag visible dans un seul snapshot Iceberg puis ecrase

Point dur : scenario Iceberg (04) — missing version-hint, allow_moved_paths workaround, scan de 19 snapshots.

## Jeanine
Format vraiment cool, voulait tester DuckDB depuis longtemps.