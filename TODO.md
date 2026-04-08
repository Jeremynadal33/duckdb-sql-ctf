* Modify data generation for misleading rows (put fake flags)

* FAIRE DES SLIDES
    * Kesako duckdb
    * Parler de WASM
    * Parler de Mother Duck
    * Disclaimer : on est pas des pros de duckdb ou iceberg
    * Orange dbt-duckdb
    * VPC Flos logs ingestion dans Snowflake -> coûts d'ingestion 800k / an Okta rex https://www.youtube.com/watch?v=TrmJilG4GXk
    * conf maxence
    * On peut gérer > 1To avec cet article https://blog.dataexpert.io/p/i-processed-1-tb-with-duckdb-in-30

* Ideas
    * Make a new lambda function that is called at hints

* Finish scenarios that we give to users
    * Remove explicit canard
    * Pour lat long to city -> mettre nom à dispo api + http_get 
    * Put hints in foldable sections qui envoie un call http async pour dire que l'utilisateur à checké son hint


* Update des scenarios
    * scenario 1 
        * enlever 'Un nombre anormalement eleve concerne le meme type de document.'
        * library_logs.zip doit être dans s3 et on doit télécharger le fichier
        * virer 'Chaque fichier .json contient une centaine d'enregistrements. "