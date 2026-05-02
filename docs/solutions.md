
# Scenario 1


### Get flag
```sql
with data as (
  select
    metadata.notes as flag_part
  from
    read_json("/Users/jeremy.nadal/repos/perso/duckdb-sql-ctf/data_generator/output/unziped")
  where
    timestamp_return is null
    and document_type = 'acte_de_naissance'
  order by
    timestamp_checkout asc
)

select
  array_to_string(array_agg(flag_part), '') as flag
from
  data
```

# Scenario 2
### Get borrower's modified id
```sql
with identities as (
  select
    *
  from
    read_json("/Users/jeremy.nadal/repos/perso/duckdb-sql-ctf/data_generator/output/unziped")
  where
    timestamp_return is null
    and document_type = 'acte_de_naissance'
)

, similar_employees as (
  select
    jaro_winkler_similarity(i.borrower_name, e.first_name || ' ' || e.last_name) AS score
    , i.borrower_name
    , e.*
  from
    read_parquet('s3://duckdb-sql-ctf/data/employees/*.parquet') as e
  cross join
    identities as i
  where
    score > 0.8
)

select
  distinct
  id
  , first_name
  , last_name
  , json(metadata).info as info
from
  similar_employees
```

### Get flag
```sql
select
  concat(
     ( select trim(json(metadata).info, '"') from read_parquet('s3://duckdb-sql-ctf/data/employees/*.parquet')
        where id = 42 )
    , (select trim(json(metadata).info, '"') from read_parquet('s3://duckdb-sql-ctf/data/badges/*.parquet')
        where employee_id = 42 )
  ) as flag
```

# Scenario 3
### Look for person

```sql
select * from postgres_db.public.persons where last_name = 'Chan'
```

### Look for his adress
```sql
select * from "postgres_db"."public"."addresses" where person_id = 448
```

### Look for the city
```sql
WITH nominatim_request AS (
    SELECT http_get(
      'https://nominatim.openstreetmap.org/reverse',
      headers => MAP {                                                                                                                                                                                                                              
        'User-Agent': 'DuckDB-Demo/1.0',
        'Accept': 'application/json'                                                                                                                                                                                                                
      },          
      params => MAP {
        'format': 'geocodejson',
        'lat': '44.837789',                                                                                                                                                                                                                      
        'lon': '-0.579187',
        'layer': 'address'                                                                                                                                                                                                                          
      }            
    ) AS response
  )
  SELECT
    (response->>'status')::INT AS status,
    json_extract_string(response->>'body', '$.features[0].properties.geocoding.label') AS address,                                                                                                                                                  
    json_extract_string(response->>'body', '$.features[0].properties.geocoding.city') AS city,
    json_extract_string(response->>'body', '$.features[0].properties.geocoding.country') AS country                                                                                                                                                 
  FROM nominatim_request;
```
### Look for city info

```sql
select * from "postgres_db"."public"."city_information" where city_name = 'Bordeaux'
```

# Scenario 4
```sql
SELECT * FROM iceberg_scan(                                                                                             
      '/Users/jeremy.nadal/repos/perso/duckdb-sql-ctf/data_generator/output/iceberg_warehouse/badges/badges'
      , allow_moved_paths = true
      , snapshot_from_timestamp = TIMESTAMP '2026-03-23 00:00:00'
  )
  where badge_id = 'BADGE-0042'
```

# Scenario 5

```sql
ATTACH 's3://duckdb-sql-ctf/data/network.duckdb' AS social (READ_ONLY);
```

```sql
with quackie as (
select * from "social"."main"."persons"
where
  first_name || ' ' || last_name = 'Quackie Chan' 
)

, first_relations as (
  select
    *
  from
    "social"."main"."relationships"
  where
    person_id_1 = (select id from quackie)
)
, first_all_ids as (
  select
    person_id_1 as person_id
  from
    first_relations
  union
  select
    person_id_2 as person_id
  from
    first_relations
)
, second_relations as (
  select
    *
  from
    "social"."main"."relationships"
  where person_id_1 in (select person_id from first_all_ids)
)
, all_ids as (
  select
    person_id
  from
    first_all_ids
  union
  select
    person_id_1 as person_id
  from
    second_relations
  union
  select
    person_id_2 as person_id
  from
    second_relations
)
select
  regexp_extract(
  notes,
  'FLAG\{[^}]+\}',
  0
) AS flag, *
from
  "social"."main"."persons"
where
 id in (select person_id from all_ids)

```


