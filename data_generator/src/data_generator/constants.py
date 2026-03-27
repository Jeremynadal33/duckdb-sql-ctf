from datetime import date

FAKER_SEED = 42

FIGURANT_NAMES = [
    "Quack Norris",
    "Quackamole",
    "Donald Quack",
    "Quackatoa",
    "Bill Quacksby",
    "Quackzilla",
    "Quack Sparrow",
    "Quackberry Finn",
    "Quack Obama",
    "Quackie Robinson",
    "Quack Black",
    "Quackie Onassis",
    "Quack Efron",
    "Quackson Pollock",
    "Quacklemore",
    "Quack Nicholson",
    "Quackira",
    "Quack White",
    "Quack Pitt",
    "Daffy Quackington",
]

QUACKIE_VARIATIONS = [
    "Quackie Chan",
    "Quack C.",
    "Quacky Chan",
    "Quackie C.",
    "Quacky Chen",
    "Quackee Chan",
]

DOCUMENT_TYPES = [
    "acte_de_naissance",
    "carte_identite",
    "permis_conduire",
    "acte_de_mariage",
    "certificat_medical",
    "diplome",
    "titre_de_propriete",
]

# Target counts for normal logs (excluding the 12 suspect birth certificates)
DOCUMENT_TYPE_WEIGHTS = {
    "acte_de_naissance": 5988,  # 6000 - 12 suspects
    "carte_identite": 10000,
    "permis_conduire": 8000,
    "acte_de_mariage": 7000,
    "certificat_medical": 9000,
    "diplome": 5000,
    "titre_de_propriete": 5000,
}

# Distribution for the 18 noise unreturned logs
NOISE_UNRETURNED_TYPES = [
    "carte_identite",
    "carte_identite",
    "carte_identite",
    "carte_identite",
    "permis_conduire",
    "permis_conduire",
    "permis_conduire",
    "acte_de_mariage",
    "acte_de_mariage",
    "acte_de_mariage",
    "acte_de_mariage",
    "certificat_medical",
    "certificat_medical",
    "certificat_medical",
    "diplome",
    "diplome",
    "titre_de_propriete",
    "titre_de_propriete",
]

NORMAL_NOTES = [
    "RAS",
    "Document en bon état",
    "",
    "Rien à signaler",
    "OK",
]

LIBRARY_BRANCH = "Bibliothèque Centrale du Lac"

DEPARTMENTS = [
    {
        "dept_id": 1,
        "dept_name": "Service Médical",
        "building": "Bâtiment A",
        "floor": 2,
    },
    {"dept_id": 2, "dept_name": "Administration", "building": "Bâtiment A", "floor": 0},
    {"dept_id": 3, "dept_name": "Informatique", "building": "Bâtiment B", "floor": 1},
    {
        "dept_id": 4,
        "dept_name": "Ressources Humaines",
        "building": "Bâtiment A",
        "floor": 1,
    },
    {"dept_id": 5, "dept_name": "Comptabilité", "building": "Bâtiment C", "floor": 0},
    {"dept_id": 6, "dept_name": "Logistique", "building": "Bâtiment D", "floor": 0},
    {"dept_id": 7, "dept_name": "Archives", "building": "Bâtiment B", "floor": -1},
    {"dept_id": 8, "dept_name": "Sécurité", "building": "Bâtiment A", "floor": 0},
    {"dept_id": 9, "dept_name": "Communication", "building": "Bâtiment C", "floor": 1},
    {"dept_id": 10, "dept_name": "Direction", "building": "Bâtiment A", "floor": 3},
]

NUM_CITIES = 500

FLAG_SCENARIO4 = "FLAG{canards_anti_criminels_mission_accomplie}"

# Placeholder — will be replaced when graph access details are defined
FLAG_SCENARIO3_PLACEHOLDER = "FLAG{graph_source=tbd,graph_access=tbd}"

BADGE_STATUSES = ["active", "expired", "revoked"]

QUACKIE_CHAN_EMPLOYEE_ID = 42
QUACKIE_CHAN_BADGE_ID = "BADGE-0042"

# Date of the big heist
# Update the following constants to get a more realistic scenario
# Like target date to the day before the ctf, target city to where the ctf is given, etc.
TARGET_DATE = date(2026, 4, 22)
TARGET_CITY = "Paris"
TARGET_LAT = 48.879226
TARGET_LON = 2.283274
DECOY_CITY = "Bordeaux"
DECOY_LAT = 44.837789
DECOY_LON = -0.579187
