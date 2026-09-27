import io

import pdfplumber

from app.services.csv_parser import ParseError
from app.services.table_reader import build_records, detect_columns, rating_values_are_usable


def _extract_table_rows(data: bytes) -> list[list]:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            tables = []
            for page in pdf.pages:
                tables.extend(page.extract_tables() or [])
    except ParseError:
        raise
    except Exception:
        raise ParseError(
            "We couldn't read this PDF. Please upload a valid PDF containing a movie table."
        )
    return tables


def parse_pdf(data: bytes) -> dict:
    if not data:
        raise ParseError("This file is empty. Please upload a PDF containing a movie table.")

    tables = _extract_table_rows(data)

    for table in tables:
        if not table or len(table) < 2:
            continue
        header = table[0] or []
        columns = detect_columns(header)
        if columns["movie"] is None:
            continue

        rows = [row for row in table[1:] if row and any(str(cell or "").strip() for cell in row)]
        if not rows:
            continue

        movie_idx = header.index(columns["movie"])
        rating_idx = header.index(columns["rating"]) if columns["rating"] else None
        id_idx = header.index(columns["movie_id"]) if columns["movie_id"] else None

        warnings = []
        if columns["rating"] is not None:
            rating_values = [
                str(row[rating_idx]).strip() if rating_idx is not None and rating_idx < len(row) else ""
                for row in rows
            ]
            non_empty = [v for v in rating_values if v]
            if non_empty and not rating_values_are_usable(non_empty):
                raise ParseError(
                    "The Rating column in this PDF doesn't contain any numbers. "
                    "Ratings must be numeric (for example 4 or 4.5)."
                )
            if not non_empty:
                columns["rating"] = None
        if columns["rating"] is None:
            warnings.append(
                "No usable Rating column was found. Movies will be added without personal ratings."
            )

        records = build_records(rows, movie_idx, rating_idx, id_idx)
        return {"records": records, "columns": columns, "warnings": warnings}

    raise ParseError(
        "We couldn't find a readable movie table in this PDF. Please upload a PDF containing "
        "a table with a Movie column (and an optional Rating column). Scanned or image-only "
        "PDFs are not supported."
    )
