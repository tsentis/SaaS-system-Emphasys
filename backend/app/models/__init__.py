"""SQLAlchemy ORM models.

Importing this package registers all models on the shared ``Base.metadata`` so that
Alembic autogenerate and ``create_all`` see them.
"""

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import Role, User, UserRole
from app.models.document import AnalysisRun, Document
from app.models.programme import FundingCall, Programme
from app.models.project import Project, ProjectPartner, WorkPackage
from app.models.organization import Organization, Person
from app.models.enrichment import Embedding, ExternalEnrichment
from app.models.governance import ApiKey, AuditLog, GdprRequest

__all__ = [
    "Base",
    "Tenant",
    "Role",
    "User",
    "UserRole",
    "AnalysisRun",
    "Document",
    "FundingCall",
    "Programme",
    "Project",
    "ProjectPartner",
    "WorkPackage",
    "Organization",
    "Person",
    "Embedding",
    "ExternalEnrichment",
    "ApiKey",
    "AuditLog",
    "GdprRequest",
]
