import io

import pandas as pd

from app.errors import UserError
from app.services.table_reader import build_records, detect_columns, rating_values_are_usable


class ParseError(UserError):
    """User-correctable input problem; carries a friendly message."""


def parse_csv(data: bytes) -> dict:
    try:
        frame = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        raise ParseError("This file is empty. Please upload a CSV with a Movie column.")
    except pd.errors.ParserError:
        raise ParseError(
            "We couldn't read this CSV file. Check that it uses commas to separate columns and try again."
        )
    except UnicodeDecodeError:
        raise ParseError("We couldn't decode this file. Please save your CSV with UTF-8 encoding.")
    except Exception:
        raise ParseError("We couldn't read this CSV file. Please check the file and try again.")

    if frame.empty or len(frame) == 0:
        raise ParseError("This file has no data rows. Please upload a CSV with at least one movie.")

    columns = detect_columns(frame.columns)
    if columns["movie"] is None:
        raise ParseError(
            "We couldn't find a movie column. Please include a column named 'Movie' or 'Title'."
        )

    warnings = []
    rating_values = []
    if columns["rating"] is not None:
        rating_values = [str(v).strip() for v in frame[columns["rating"]].tolist()]
        non_empty = [v for v in rating_values if v]
        if non_empty and not rating_values_are_usable(non_empty):
            raise ParseError(
                "The Rating column doesn't contain any numbers. Ratings must be numeric "
                "(for example 4 or 4.5). Please fix the column and re-upload."
            )
        if not non_empty:
            columns["rating"] = None
    if columns["rating"] is None:
        warnings.append("No usable Rating column was found. Movies will be added without personal ratings.")

    records = build_records(
        frame.values.tolist(),
        movie_idx=list(frame.columns).index(columns["movie"]),
        rating_idx=list(frame.columns).index(columns["rating"]) if columns["rating"] else None,
        id_idx=list(frame.columns).index(columns["movie_id"]) if columns["movie_id"] else None,
    )

    return {"records": records, "columns": columns, "warnings": warnings}
