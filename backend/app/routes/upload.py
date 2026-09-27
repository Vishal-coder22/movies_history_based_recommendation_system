import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import MAX_FILE_SIZE_MB
from app.database.connection import get_db
from app.database.repositories import ImportRepository
from app.deps import get_current_user_id
from app.errors import UserError
from app.services.csv_parser import parse_csv
from app.services.data_cleaner import confirm_import, resolve_matches, run_cleaning
from app.services.pdf_parser import parse_pdf

router = APIRouter(prefix="/api", tags=["imports"])

CSV_EXTENSIONS = {".csv"}
PDF_EXTENSIONS = {".pdf"}

SAMPLE_ROWS = 20


def _safe_filename(original: str | None, kind: str) -> str:
    if not original or not original.strip():
        raise UserError(f"No file was selected. Please choose a {kind.upper()} file.")
    base = os.path.basename(original.replace("\\", "/"))
    base = re.sub(r"[^\w.\- ]+", "_", base).strip(" .")
    return (base or f"upload.{kind}")[:120]


async def _read_upload(file: UploadFile, allowed: set[str], kind: str) -> tuple[str, bytes]:
    name = _safe_filename(file.filename, kind)
    extension = os.path.splitext(name)[1].lower()
    if extension not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise UserError(f"Unsupported file type '{extension or 'none'}'. Please upload a {allowed_text} file.")

    data = await file.read()
    if not data:
        raise UserError(f"This file is empty. Please upload a {kind.upper()} file with your movie history.")
    if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise UserError(
            f"This file is larger than {MAX_FILE_SIZE_MB} MB. Please upload a smaller file."
        )
    return name, data


def _sample_rows(records: list[dict]) -> list[dict]:
    return [
        {
            "record_id": record["record_id"],
            "raw_movie_title": record["raw_movie_title"],
            "raw_rating": record["raw_rating"],
            "match_status": record["match_status"],
        }
        for record in records[:SAMPLE_ROWS]
    ]


def _warnings_for(records: list[dict], columns: dict) -> list[str]:
    warnings = []
    if not columns.get("rating"):
        warnings.append(
            "No usable Rating column was found. Movies will be added without personal ratings."
        )
    elif not any(record.get("raw_rating") not in (None, "") for record in records):
        warnings.append("The Rating column is empty in every row. Ratings were left blank.")
    return warnings


def _preview_payload(db, import_row: dict) -> dict:
    records = ImportRepository.get_records(db, import_row["import_id"])
    return {
        "import_id": import_row["import_id"],
        "file_name": import_row["file_name"],
        "file_type": import_row["file_type"],
        "status": import_row["status"],
        "total_rows": import_row["total_rows"],
        "columns": import_row.get("columns") or {},
        "warnings": _warnings_for(records, import_row.get("columns") or {}),
        "sample_rows": _sample_rows(records),
        "report": ImportRepository.get_quality_report(db, import_row["import_id"]),
    }


def _owned_import(db, import_id: int, user_id: int) -> dict:
    import_row = ImportRepository.get_by_id(db, import_id)
    if import_row is None or import_row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="We couldn't find that import.")
    return import_row


def _create_import(db, user_id: int, name: str, file_type: str, parsed: dict) -> dict:
    records = parsed["records"]
    import_id = ImportRepository.create(
        db, user_id, name, file_type, parsed["columns"], total_rows=len(records)
    )
    ImportRepository.add_records(db, import_id, records)
    import_row = ImportRepository.get_by_id(db, import_id)
    return _preview_payload(db, import_row)


@router.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    name, data = await _read_upload(file, CSV_EXTENSIONS, "csv")
    parsed = parse_csv(data)
    return _create_import(db, user_id, name, "csv", parsed)


@router.post("/upload/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    name, data = await _read_upload(file, PDF_EXTENSIONS, "pdf")
    parsed = parse_pdf(data)
    return _create_import(db, user_id, name, "pdf", parsed)


@router.get("/imports/{import_id}")
def get_import(
    import_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    import_row = _owned_import(db, import_id, user_id)
    return _preview_payload(db, import_row)


@router.get("/imports/{import_id}/preview")
def preview_import(
    import_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    import_row = _owned_import(db, import_id, user_id)
    return _preview_payload(db, import_row)


@router.post("/imports/{import_id}/clean")
def clean_import(
    import_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _owned_import(db, import_id, user_id)
    try:
        return run_cleaning(db, import_id)
    except UserError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)


class MatchDecision(BaseModel):
    record_id: int
    movie_id: int | None = None


class ConfirmMatchesInput(BaseModel):
    decisions: list[MatchDecision]


@router.post("/imports/{import_id}/confirm-matches")
def confirm_matches(
    import_id: int,
    body: ConfirmMatchesInput,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _owned_import(db, import_id, user_id)
    try:
        return resolve_matches(db, import_id, [d.model_dump() for d in body.decisions])
    except UserError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)


@router.post("/imports/{import_id}/confirm")
def confirm(
    import_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _owned_import(db, import_id, user_id)
    try:
        return confirm_import(db, import_id, user_id)
    except UserError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
