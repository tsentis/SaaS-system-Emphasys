"""Export endpoints: projects as CSV / XLSX / PDF / Word."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.services import export_service, project_service

router = APIRouter(tags=["export"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _attachment(data: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects.csv")
def export_csv(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Response:
    data = export_service.to_csv(project_service.list_projects(db))
    return _attachment(data, "text/csv", "projects.csv")


@router.get("/projects.xlsx")
def export_xlsx(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Response:
    data = export_service.to_xlsx(project_service.list_projects(db))
    return _attachment(data, _XLSX, "projects.xlsx")


@router.get("/projects.docx")
def export_docx(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Response:
    data = export_service.to_docx(project_service.list_projects(db))
    return _attachment(data, _DOCX, "projects.docx")


@router.get("/projects.pdf")
def export_pdf(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> Response:
    data = export_service.to_pdf(project_service.list_projects(db))
    return _attachment(data, "application/pdf", "projects.pdf")
