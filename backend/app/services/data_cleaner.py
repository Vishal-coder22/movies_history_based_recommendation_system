"""Data cleaning: duplicates, missing values, invalid records, quality report,
movie matching, match resolution and final confirmation."""

import json

from app.config import RATING_MAX, RATING_MIN
from app.errors import UserError
from app.services.movie_matcher import match_title
from app.services.table_reader import normalize_title


def coerce_rating(raw) -> tuple[float | None, bool]:
    """Return (value, is_invalid). Absent/empty input is not invalid - it is missing."""
    if raw is None or str(raw).strip() == "":
        return None, False
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None, True
    if value < RATING_MIN or value > RATING_MAX:
        return None, True
    return value, False


def clean_records(records: list[dict]) -> list[dict]:
    """Annotate raw records with normalized titles, validity and duplicate flags."""
    seen: set[str] = set()
    cleaned = []
    for record in records:
        raw_title = record.get("raw_movie_title")
        title = str(raw_title).strip() if raw_title is not None else ""
        normalized = normalize_title(title)
        rating, invalid_rating = coerce_rating(record.get("raw_rating"))

        is_valid = bool(normalized) and not invalid_rating

        is_duplicate = False
        if is_valid:
            if normalized in seen:
                is_duplicate = True
            else:
                seen.add(normalized)

        cleaned.append(
            {
                "record_id": record.get("record_id"),
                "raw_movie_title": title or None,
                "raw_movie_id": record.get("raw_movie_id"),
                "raw_rating": record.get("raw_rating"),
                "normalized_title": normalized or None,
                "coerced_rating": rating,
                "is_valid": int(is_valid),
                "is_duplicate": int(is_duplicate),
            }
        )
    return cleaned


def recompute_report(conn, import_id: int) -> dict:
    """Count record outcomes. Every record falls in exactly one bucket:
    duplicate | missing | invalid | matched | ambiguous | unmatched (| pending)."""
    from app.database.repositories import ImportRepository

    records = ImportRepository.get_records(conn, import_id)
    report = {
        "original_rows": len(records),
        "duplicate_rows": 0,
        "missing_movie_rows": 0,
        "invalid_rows": 0,
        "matched_rows": 0,
        "ambiguous_rows": 0,
        "unmatched_rows": 0,
        "final_rows": 0,
    }
    for record in records:
        if record["is_duplicate"]:
            report["duplicate_rows"] += 1
        elif not record["is_valid"]:
            if record["normalized_title"]:
                report["invalid_rows"] += 1
            else:
                report["missing_movie_rows"] += 1
        else:
            status = record["match_status"]
            if status == "matched":
                report["matched_rows"] += 1
            elif status == "ambiguous":
                report["ambiguous_rows"] += 1
            elif status == "unmatched":
                report["unmatched_rows"] += 1
    report["final_rows"] = report["matched_rows"]
    return report


def _save_report(conn, import_id: int, report: dict) -> None:
    from app.database.repositories import ImportRepository

    ImportRepository.save_quality_report(conn, import_id, report)


def _status_for(report: dict) -> str:
    return "awaiting_match" if report["ambiguous_rows"] > 0 else "cleaned"


def run_cleaning(conn, import_id: int) -> dict:
    """Clean, match and persist an import; returns report + lists for the UI."""
    from app.database.repositories import ImportRepository

    records = ImportRepository.get_records(conn, import_id)
    if not records:
        raise UserError("This import has no records to clean.")

    cleaned = clean_records(records)

    for record in cleaned:
        if record["is_valid"] and not record["is_duplicate"]:
            match = match_title(conn, record["normalized_title"], record["raw_movie_id"])
        else:
            match = {"status": "skipped", "movie_id": None, "candidates": []}

        ImportRepository.update_record(
            conn,
            record["record_id"],
            raw_movie_title=record["raw_movie_title"],
            normalized_title=record["normalized_title"],
            is_valid=record["is_valid"],
            is_duplicate=record["is_duplicate"],
            match_status=match["status"],
            matched_movie_id=match["movie_id"],
            match_candidates=json.dumps(match["candidates"]) if match["candidates"] else None,
        )

    report = recompute_report(conn, import_id)
    _save_report(conn, import_id, report)
    ImportRepository.update_status(conn, import_id, _status_for(report))

    return {
        "report": report,
        "ambiguous": _records_with_status(conn, import_id, "ambiguous"),
        "unmatched": _records_with_status(conn, import_id, "unmatched"),
        "status": _status_for(report),
    }


def _records_with_status(conn, import_id: int, status: str) -> list[dict]:
    from app.database.repositories import ImportRepository
    from app.services.movie_matcher import parse_candidates

    out = []
    for record in ImportRepository.get_records(conn, import_id):
        if record["match_status"] != status:
            continue
        item = {
            "record_id": record["record_id"],
            "raw_movie_title": record["raw_movie_title"],
            "normalized_title": record["normalized_title"],
        }
        if status == "ambiguous":
            item["candidates"] = parse_candidates(record.get("match_candidates"))
        out.append(item)
    return out


def resolve_matches(conn, import_id: int, decisions: list[dict]) -> dict:
    """Apply the user's choices for ambiguous/unmatched records.

    decisions: [{'record_id': int, 'movie_id': int|None}, ...]
    movie_id present -> use that catalogue movie; movie_id null -> skip the record.
    """
    from app.database.repositories import ImportRepository, MovieRepository

    if not decisions:
        raise UserError("Select a movie for each record, or skip it.")

    records = {r["record_id"]: r for r in ImportRepository.get_records(conn, import_id)}

    for decision in decisions:
        record_id = decision.get("record_id")
        movie_id = decision.get("movie_id")

        record = records.get(record_id)
        if record is None:
            raise UserError("One of the selected records no longer exists. Re-run cleaning.")

        if movie_id is not None:
            if MovieRepository.get_by_id(conn, movie_id) is None:
                raise UserError("One of the selected movies no longer exists. Please try again.")
        ImportRepository.set_match_decision(conn, record_id, movie_id)

    report = recompute_report(conn, import_id)
    _save_report(conn, import_id, report)
    ImportRepository.update_status(conn, import_id, _status_for(report))

    return {
        "report": report,
        "ambiguous": _records_with_status(conn, import_id, "ambiguous"),
        "unmatched": _records_with_status(conn, import_id, "unmatched"),
        "status": _status_for(report),
    }


def confirm_import(conn, import_id: int, user_id: int) -> dict:
    """Insert every matched record into the user's watched list."""
    from app.database.repositories import ImportRepository, WatchedMovieRepository

    report = recompute_report(conn, import_id)
    if report["ambiguous_rows"] > 0:
        raise UserError(
            f"You have {report['ambiguous_rows']} ambiguous match(es) to resolve before "
            "confirming. Choose the correct movie for each one, or skip it.",
            status_code=409,
        )

    import_run = ImportRepository.get_by_id(conn, import_id) or {}
    source = import_run.get("file_type", "csv")
    if source not in ("csv", "pdf"):
        source = "csv"

    existing = WatchedMovieRepository.get_movie_ids(conn, user_id)
    inserted = 0
    already_watched = 0

    for record in ImportRepository.get_records(conn, import_id):
        if record["match_status"] != "matched":
            continue
        movie_id = record["matched_movie_id"]
        if movie_id in existing:
            already_watched += 1
            continue
        rating, invalid = coerce_rating(record.get("raw_rating"))
        WatchedMovieRepository.add(conn, user_id, movie_id, None if invalid else rating, source)
        existing.add(movie_id)
        inserted += 1

    ImportRepository.update_status(conn, import_id, "completed")
    return {
        "inserted": inserted,
        "already_watched": already_watched,
        "unmatched_skipped": report["unmatched_rows"],
        "report": report,
        "status": "completed",
    }
