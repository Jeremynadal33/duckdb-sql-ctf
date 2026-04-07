"""Tests for scenario 3 — PostgreSQL data generation (unit tests only, no DB)."""

from datetime import date

from faker import Faker

from data_generator.constants import (
    DECOY_CITY,
    FAKER_SEED,
    GH_PAGES_BASE_URL,
    NUM_CITIES,
    TARGET_CITY,
)
from data_generator.generators.scenario3_postgres import (
    _create_cities,
    _create_key_persons,
    _generate_city_names,
    build_scenario3_flag,
)
from data_generator.models.pg_models import Address, CityInformation, Person, Profession


def _make_fake() -> Faker:
    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    return fake


class TestKeyPersons:
    def test_three_key_persons_created(self):
        persons = _create_key_persons()
        assert len(persons) == 3

    def test_quackie_chan(self):
        persons = _create_key_persons()
        quackie = next(p for p in persons if p.first_name == "Quackie")
        assert quackie.last_name == "Chan"

    def test_hugh_quackman(self):
        persons = _create_key_persons()
        hugh = next(p for p in persons if p.first_name == "Hugh")
        assert hugh.last_name == "Quackman"

    def test_donna_duck(self):
        persons = _create_key_persons()
        donna = next(p for p in persons if p.first_name == "Donna")
        assert donna.last_name == "Duck"


class TestCities:
    def test_city_count(self):
        fake = _make_fake()
        cities = _create_cities(fake)
        assert len(cities) == NUM_CITIES

    def test_target_and_decoy_present(self):
        fake = _make_fake()
        cities = _create_cities(fake)
        city_names = [c.city_name for c in cities]
        assert TARGET_CITY in city_names
        assert DECOY_CITY in city_names

    def test_decoy_has_flag(self):
        fake = _make_fake()
        cities = _create_cities(fake)
        decoy = next(c for c in cities if c.city_name == DECOY_CITY)
        expected_flag = build_scenario3_flag()
        assert decoy.city_metadata["info"] == expected_flag
        assert GH_PAGES_BASE_URL in expected_flag
        assert expected_flag.startswith("FLAG{")
        assert expected_flag.endswith("}")
        assert ".md" in expected_flag

    def test_target_has_hint(self):
        fake = _make_fake()
        cities = _create_cities(fake)
        target = next(c for c in cities if c.city_name == TARGET_CITY)
        assert "carte" in target.city_metadata["info"]

    def test_target_and_decoy_have_high_ids_position(self):
        """TARGET_CITY and DECOY_CITY should be at the end of the list (high IDs)."""
        fake = _make_fake()
        cities = _create_cities(fake)
        assert cities[-2].city_name == TARGET_CITY
        assert cities[-1].city_name == DECOY_CITY

    def test_generated_city_names_exclude_target_decoy(self):
        fake = _make_fake()
        names = _generate_city_names(fake)
        assert TARGET_CITY not in names
        assert DECOY_CITY not in names
        assert len(names) == NUM_CITIES - 2


class TestModels:
    def test_person_instantiation(self):
        p = Person(first_name="Test", last_name="Duck", date_of_birth=date(2000, 1, 1))
        assert p.first_name == "Test"

    def test_profession_instantiation(self):
        p = Profession(person_id=1, title="Médecin", employer="Clinique")
        assert p.title == "Médecin"

    def test_address_instantiation(self):
        a = Address(person_id=1, latitude=44.8, longitude=-0.5)
        assert a.is_current is True

    def test_city_information_instantiation(self):
        c = CityInformation(city_name="Bordeaux", city_metadata={"info": "test"})
        assert c.city_name == "Bordeaux"
