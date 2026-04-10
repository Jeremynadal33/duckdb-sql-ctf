
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
