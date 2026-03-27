from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Column
from sqlalchemy import JSON as SA_JSON
from sqlmodel import Field, SQLModel


class Person(SQLModel, table=True):
    __tablename__ = "persons"

    id: int | None = Field(default=None, primary_key=True)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    date_of_birth: date | None = None


class Profession(SQLModel, table=True):
    __tablename__ = "professions"

    id: int | None = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="persons.id")
    title: str = Field(max_length=100)
    employer: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None


class Address(SQLModel, table=True):
    __tablename__ = "addresses"

    id: int | None = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="persons.id")
    latitude: float
    longitude: float
    is_current: bool = True


class CityInformation(SQLModel, table=True):
    __tablename__ = "city_information"

    id: int | None = Field(default=None, primary_key=True)
    city_name: str = Field(max_length=100)
    city_metadata: Any = Field(default=None, sa_column=Column("metadata", SA_JSON))


class Relationship(SQLModel, table=True):
    __tablename__ = "relationships"

    id: int | None = Field(default=None, primary_key=True)
    person_id_1: int = Field(foreign_key="persons.id")
    person_id_2: int = Field(foreign_key="persons.id")
    relationship_type: str
    notes: str | None = None
