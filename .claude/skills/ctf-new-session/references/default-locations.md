# Adresses & coordonnées par défaut

Tableau de référence pour le skill `ctf-new-session`. Charger ce fichier après que l'utilisateur a indiqué la ville du CTF, pour proposer les valeurs decoy par défaut.

## Règle de mapping decoy

| Lieu du CTF | Decoy / scène |
|---|---|
| **Bordeaux** | Paris (Bassin de la Villette) |
| **Paris** | Bordeaux (Lac de Bordeaux) |
| **Autre** (Lyon, Nantes, Toulouse, …) | Bordeaux (default fallback) |

## Decoy = Paris (CTF à Bordeaux)

Plan d'eau de référence pour le journal : **Bassin de la Villette**.

| Constante | Valeur | Adresse / lieu |
|---|---|---|
| `LIBRARY_CITY` | `"Paris"` | Bibliothèque François-Mitterrand (BNF Tolbiac), Quai François Mauriac, 75013 |
| `LIBRARY_LAT` | `48.83323` | |
| `LIBRARY_LON` | `2.37653` | |
| `ARCHIVES_CITY` | `"Paris"` | Archives de Paris, 18 boulevard Sérurier, 75019 |
| `ARCHIVES_LAT` | `48.88210` | |
| `ARCHIVES_LON` | `2.40140` | |
| `CITY_HALL_CITY` | `"Paris"` | Mairie de Paris Centre, 2 rue Eugène Spuller, 75003 |
| `CITY_HALL_LAT` | `48.86386` | |
| `CITY_HALL_LON` | `2.36258` | |
| `QUACKIE_CITY` | `"Paris"` | Baignade estivale, Bassin de la Villette, Quai de la Loire, 75019 |
| `QUACKIE_LAT` | `48.88974` | |
| `QUACKIE_LON` | `2.38209` | |

## Decoy = Bordeaux (CTF à Paris ou ailleurs)

Plan d'eau de référence pour le journal : **Lac de Bordeaux**.

| Constante | Valeur | Adresse / lieu |
|---|---|---|
| `LIBRARY_CITY` | `"Bordeaux"` | Bibliothèque (proche Lac de Bordeaux) |
| `LIBRARY_LAT` | `44.87383720544609` | |
| `LIBRARY_LON` | `-0.5728187300381997` | |
| `ARCHIVES_CITY` | `"Bordeaux"` | Archives Bordeaux Métropole |
| `ARCHIVES_LAT` | `44.847105194415995` | |
| `ARCHIVES_LON` | `-0.5539175146997978` | |
| `CITY_HALL_CITY` | `"Bordeaux"` | Hôtel de Ville (Palais Rohan) |
| `CITY_HALL_LAT` | `44.84003190271778` | |
| `CITY_HALL_LON` | `-0.5788558745417992` | |
| `QUACKIE_CITY` | `"Bordeaux"` | Domicile près du Lac de Bordeaux |
| `QUACKIE_LAT` | `44.883994690921455` | |
| `QUACKIE_LON` | `-0.5783725032146239` | |

## Lieux du CTF connus (planque finale = `TARGET_*`)

À utiliser si l'utilisateur cite simplement un site Ippon sans donner de coordonnées :

| Site | Adresse | `TARGET_LAT` | `TARGET_LON` |
|---|---|---|---|
| **Ippon Technologies Bordeaux** | 44 Allées de Tourny, 33000 Bordeaux | `44.844259` | `-0.576987` |

Pour tout autre lieu, demander à l'utilisateur l'adresse complète et géocoder soi-même (ou suggérer qu'il fournisse les coordonnées exactes — important car le scénario 6 fait du reverse-geocoding via Nominatim et la précision compte).

## Mois français pour le filename du journal

Le filename `le-canard-enchaine-<jour>-<mois>-<année>.md` utilise le mois en français minuscule, sans accent dans certains cas. La logique exacte vient de `data_generator/src/data_generator/generators/scenario3_postgres.py:FRENCH_MONTHS` :

```
janvier, février, mars, avril, mai, juin,
juillet, août, septembre, octobre, novembre, décembre
```

Exemples :
- `2026-04-27` → `le-canard-enchaine-27-avril-2026.md`
- `2026-08-12` → `le-canard-enchaine-12-août-2026.md`
- `2026-02-03` → `le-canard-enchaine-3-février-2026.md` (pas de zero-padding du jour)
