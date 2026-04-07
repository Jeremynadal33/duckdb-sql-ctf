from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class LogMetadata(BaseModel):
    library_branch: str
    notes: str


class LibraryLog(BaseModel):
    log_id: str
    document_type: str
    document_title: str
    borrower_name: str
    timestamp_checkout: datetime
    timestamp_return: datetime | None
    metadata: LogMetadata
