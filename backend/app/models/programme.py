"""EU funding programmes and calls (shared reference data)."""

import uuid
from datetime import date

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPrimaryKey


class Programme(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "programmes"

    # Erasmus+, Horizon Europe, CERV, Interreg, AMIF, Digital Europe, …
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(unique=True)


class FundingCall(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "funding_calls"

    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    identifier: Mapped[str | None] = mapped_column(index=True)
    title: Mapped[str | None] = mapped_column()
    deadline: Mapped[date | None] = mapped_column()
    total_budget: Mapped[float | None] = mapped_column(Numeric(18, 2))
