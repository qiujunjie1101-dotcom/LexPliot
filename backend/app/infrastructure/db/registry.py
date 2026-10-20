import app.infrastructure.idempotency  # noqa: F401
import app.modules.auth.models  # noqa: F401
from app.infrastructure.db.base import Base

__all__ = ["Base"]
