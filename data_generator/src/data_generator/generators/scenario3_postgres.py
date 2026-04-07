"""Scenario 3 — Populate PostgreSQL tables (persons, professions, addresses, city_information)."""

from __future__ import annotations

import json
import random
from datetime import date

from faker import Faker
from sqlmodel import Session, SQLModel, create_engine

from data_generator.config import CTFConfig
from data_generator.constants import (
    DECOY_CITY,
    DECOY_LAT,
    DECOY_LON,
    FAKER_SEED,
    FIGURANT_NAMES,
    GH_PAGES_BASE_URL,
    NUM_CITIES,
    QUACKIE_DEATH_DATE,
    TARGET_CITY,
    TARGET_DATE,
    TARGET_LAT,
    TARGET_LON,
)
from data_generator.models.pg_models import Address, CityInformation, Person, Profession

NUM_TOTAL_PERSONS = 450
NUM_TOTAL_PROFESSIONS = 550
NUM_TOTAL_ADDRESSES = 1000

# France region bounding box for random coordinates
LAT_MIN, LAT_MAX = 43.293200, 51.069017
LON_MIN, LON_MAX = -4.790039, 7.778320

PROFESSIONS_FR = [
    "Enseignant",
    "Ingénieur",
    "Comptable",
    "Infirmier",
    "Avocat",
    "Architecte",
    "Journaliste",
    "Pharmacien",
    "Boulanger",
    "Mécanicien",
    "Électricien",
    "Plombier",
    "Chef cuisinier",
    "Bibliothécaire",
    "Dentiste",
    "Vétérinaire",
    "Psychologue",
    "Chauffeur",
    "Secrétaire",
    "Agent immobilier",
]

EMPLOYERS_FR = [
    "Mairie de Bordeaux",
    "CHU de Bordeaux",
    "Université de Bordeaux",
    "Lycée Montaigne",
    "Collège Aliénor",
    "Clinique Saint-Martin",
    "Cabinet Dupont & Associés",
    "Boulangerie du Lac",
    "Garage Central",
    "Pharmacie de la Place",
    "Bibliothèque Municipale",
    "École Primaire Jules Ferry",
    "Restaurant Le Canard Doré",
    "Hôtel des Quais",
    "Banque Populaire Aquitaine",
]

CITY_NOISE_NOTES = [
    "rien à signaler",
    "rien à voir ici",
    "zone résidentielle calme",
    "pas d'anomalie détectée",
    "quartier tranquille",
]


FRENCH_MONTHS = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def build_scenario3_flag() -> str:
    """Compute the scenario 3 flag — a link to the hidden article on GH Pages."""
    d = QUACKIE_DEATH_DATE
    filename = f"le-canard-enchaine-{d.day}-{FRENCH_MONTHS[d.month]}-{d.year}.md"
    return f"FLAG{{{GH_PAGES_BASE_URL}/{filename}}}"


def _engine_url(config: CTFConfig) -> str:
    return (
        f"postgresql+psycopg2://{config.pg_master_user}:{config.pg_master_password}"
        f"@{config.db_host}:{config.db_port}/{config.db_name}"
    )


def _create_key_persons() -> list[Person]:
    """Create the key characters with known data."""
    return [
        Person(
            first_name="Quackie",
            last_name="Chan",
            date_of_birth=date(1978, 9, 3),
        ),
        Person(
            first_name="Hugh",
            last_name="Quackman",
            date_of_birth=date(1975, 6, 12),
        ),
        Person(
            first_name="Donna",
            last_name="Duck",
            date_of_birth=date(1980, 1, 22),
        ),
    ]


def _create_figurant_persons(fake: Faker) -> list[Person]:
    """Create persons from the figurant name list."""
    persons: list[Person] = []
    for name in FIGURANT_NAMES:
        parts = name.split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        persons.append(
            Person(
                first_name=first,
                last_name=last,
                date_of_birth=fake.date_of_birth(minimum_age=20, maximum_age=70),
            )
        )
    return persons


def _create_filler_persons(fake: Faker, count: int) -> list[Person]:
    """Create random filler persons."""
    persons: list[Person] = []
    for _ in range(count):
        persons.append(
            Person(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80),
            )
        )
    return persons


def _create_professions(fake: Faker, persons: list[Person]) -> list[Profession]:
    """Create professions for all persons. Key characters get specific professions."""
    professions: list[Profession] = []

    for person in persons:
        pid = person.id
        assert pid is not None

        if person.first_name == "Quackie" and person.last_name == "Chan":
            professions.append(
                Profession(
                    person_id=pid,
                    title="Médecin généraliste",
                    employer="Clinique du Lac",
                    start_date=TARGET_DATE.replace(year=TARGET_DATE.year - 20),
                    end_date=None,
                )
            )
        elif person.first_name == "Hugh" and person.last_name == "Quackman":
            professions.append(
                Profession(
                    person_id=pid,
                    title="Professeur de sport",
                    employer="Lycée du Lac",
                    start_date=TARGET_DATE.replace(year=TARGET_DATE.year - 15),
                    end_date=None,
                )
            )
        elif person.first_name == "Donna" and person.last_name == "Duck":
            professions.append(
                Profession(
                    person_id=pid,
                    title="Assistante maternelle",
                    employer="Crèche du Lac",
                    start_date=TARGET_DATE.replace(year=TARGET_DATE.year - 13),
                    end_date=None,
                )
            )
        else:
            # 1 or 2 professions per person
            num_profs = fake.random_element([1, 1, 1, 2])
            for j in range(num_profs):
                start = fake.date_between(
                    start_date=TARGET_DATE.replace(year=TARGET_DATE.year - 25),
                    end_date=TARGET_DATE.replace(year=TARGET_DATE.year - 3),
                )
                end = (
                    None
                    if j == num_profs - 1
                    else fake.date_between(
                        start_date=start,
                        end_date=TARGET_DATE.replace(year=TARGET_DATE.year - 2),
                    )
                )
                professions.append(
                    Profession(
                        person_id=pid,
                        title=fake.random_element(PROFESSIONS_FR),
                        employer=fake.random_element(EMPLOYERS_FR),
                        start_date=start,
                        end_date=end,
                    )
                )

    return professions


def _create_addresses(fake: Faker, persons: list[Person]) -> list[Address]:
    """Create addresses for all persons. Key characters get specific coordinates."""
    addresses: list[Address] = []

    for person in persons:
        pid = person.id
        assert pid is not None

        if person.first_name == "Quackie" and person.last_name == "Chan":
            # Quackie Chan (the doctor) — geocoding his address leads to the flag
            addresses.append(
                Address(
                    person_id=pid,
                    latitude=DECOY_LAT,
                    longitude=DECOY_LON,
                    is_current=True,
                )
            )
            # Historical address nearby
            addresses.append(
                Address(
                    person_id=pid,
                    latitude=DECOY_LAT
                    + 0.01
                    + fake.pyfloat(min_value=-0.02, max_value=0.02),
                    longitude=DECOY_LON
                    + 0.01
                    + fake.pyfloat(min_value=-0.02, max_value=0.02),
                    is_current=False,
                )
            )
        elif person.first_name == "Hugh" and person.last_name == "Quackman":
            # Hugh Quackman (the suspect) — address in target city
            addresses.append(
                Address(
                    person_id=pid,
                    latitude=TARGET_LAT,
                    longitude=TARGET_LON,
                    is_current=True,
                )
            )
            addresses.append(
                Address(
                    person_id=pid,
                    latitude=DECOY_LAT + fake.pyfloat(min_value=-0.02, max_value=0.02),
                    longitude=DECOY_LON + fake.pyfloat(min_value=-0.02, max_value=0.02),
                    is_current=False,
                )
            )
        else:
            # 1-3 addresses per person
            num_addr = fake.random_element([1, 2, 2, 3])
            for j in range(num_addr):
                is_current = j == num_addr - 1
                lat = fake.pyfloat(min_value=LAT_MIN, max_value=LAT_MAX)
                lon = fake.pyfloat(min_value=LON_MIN, max_value=LON_MAX)
                addresses.append(
                    Address(
                        person_id=pid,
                        latitude=lat,
                        longitude=lon,
                        is_current=is_current,
                    )
                )

    return addresses


def _generate_city_names(fake: Faker) -> list[str]:
    """Generate a deduplicated list of city names using Faker, ensuring target/decoy are included."""
    cities: set[str] = set()
    # Generate until we have enough unique cities (excluding target/decoy which are added separately)
    while len(cities) < NUM_CITIES - 2:
        city = fake.city()
        if city not in (TARGET_CITY, DECOY_CITY):
            cities.add(city)
    return sorted(cities)


def _create_cities(fake: Faker) -> list[CityInformation]:
    """Create city_information rows with flags/hints.

    Noise cities are returned first so that TARGET_CITY and DECOY_CITY
    get higher auto-increment IDs.
    """
    noise_city_names = _generate_city_names(fake)

    cities: list[CityInformation] = []

    # Noise cities first (low IDs)
    for city_name in noise_city_names:
        noise = CITY_NOISE_NOTES[hash(city_name) % len(CITY_NOISE_NOTES)]
        metadata = {"info": noise}
        cities.append(CityInformation(city_name=city_name, city_metadata=metadata))

    # Target and decoy cities last (high IDs)
    cities.append(
        CityInformation(
            city_name=TARGET_CITY,
            city_metadata={
                "info": "en vrai c'est vraiment pas loin là, check ptet sur une carte"
            },
        )
    )
    cities.append(
        CityInformation(
            city_name=DECOY_CITY,
            city_metadata={"info": build_scenario3_flag()},
        )
    )

    return cities


def _upload_answer_to_s3(config: CTFConfig) -> None:
    """Upload the scenario 3 answer file to S3."""
    import boto3

    s3 = boto3.client("s3")
    flag = build_scenario3_flag()
    s3.put_object(
        Bucket=config.s3_bucket_name,
        Key="leaderboard/answers/scenario_3.txt",
        Body=flag.encode("utf-8"),
    )


def populate_postgres(config: CTFConfig, upload: bool = True) -> None:
    """Create tables and populate them with data."""
    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    engine = create_engine(
        _engine_url(config),
        echo=False,
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    )

    # Create tables (drop existing first for idempotency)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # --- Persons ---
        # Insert filler + figurant persons first so they get low IDs
        figurant_persons = _create_figurant_persons(fake)
        key_persons = _create_key_persons()
        filler_count = NUM_TOTAL_PERSONS - len(key_persons) - len(figurant_persons)
        filler_persons = _create_filler_persons(fake, filler_count)

        non_key_persons = figurant_persons + filler_persons
        session.add_all(non_key_persons)
        session.flush()  # Assign low IDs to non-key persons

        # Key persons get high IDs
        session.add_all(key_persons)
        session.flush()

        all_persons = non_key_persons + key_persons

        # --- Professions ---
        professions = _create_professions(fake, all_persons)
        # Trim or pad to target
        if len(professions) > NUM_TOTAL_PROFESSIONS:
            professions = professions[:NUM_TOTAL_PROFESSIONS]
        session.add_all(professions)

        # --- Addresses ---
        addresses = _create_addresses(fake, all_persons)
        # Trim to target
        if len(addresses) > NUM_TOTAL_ADDRESSES:
            addresses = addresses[:NUM_TOTAL_ADDRESSES]
        session.add_all(addresses)

        # --- City information ---
        cities = _create_cities(fake)
        session.add_all(cities)

        session.commit()

    # Upload answer file to S3
    if upload:
        _upload_answer_to_s3(config)
