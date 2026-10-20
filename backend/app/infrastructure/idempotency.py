import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.exceptions import IdempotencyConflict
from app.infrastructure.db.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def request_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdempotencyService:
    """幂等键查询与记录；提交事务由调用方 Service 负责。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self,
        tenant_id: UUID,
        key: str,
        payload_hash: str,
    ) -> IdempotencyKey | None:
        row = self.session.get(IdempotencyKey, (tenant_id, key))
        if row is None:
            return None
        if row.expires_at <= datetime.now(UTC):
            self.session.delete(row)
            return None
        if row.request_hash != payload_hash:
            raise IdempotencyConflict()
        return row

    def save(
        self,
        tenant_id: UUID,
        key: str,
        payload_hash: str,
        status: int,
        body: dict[str, Any],
    ) -> None:
        self.session.add(
            IdempotencyKey(
                tenant_id=tenant_id,
                key=key,
                request_hash=payload_hash,
                response_status=status,
                response_body=body,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
            )
        )


__all__ = ["IdempotencyKey", "IdempotencyService", "request_hash"]
