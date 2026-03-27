from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Employee(BaseModel):
    id: int
    first_name: str
    last_name: str
    department_id: int
    hire_date: date
    email: str
    metadata: str  # JSON string, e.g. '{"info": "..."}'


class Badge(BaseModel):
    badge_id: str
    employee_id: int
    issued_date: date
    status: str  # active, inactive, revoked, expired
    metadata: str  # JSON string


class Department(BaseModel):
    dept_id: int
    dept_name: str
    building: str
    floor: int
