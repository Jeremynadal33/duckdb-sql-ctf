from __future__ import annotations

from pydantic import BaseModel


class Building(BaseModel):
    id: int
    nom: str
    type: str  # bibliothèque, mairie, école, hôpital, ...
    message: str  # vide pour les décoys ; contient le flag pour la bibliothèque
