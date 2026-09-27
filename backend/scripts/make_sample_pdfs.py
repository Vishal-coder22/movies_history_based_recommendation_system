"""Generate sample table PDFs used by tests and the demo.

Run from the project root:
    .venv/Scripts/python.exe backend/scripts/make_sample_pdfs.py
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures")


def make_table_pdf(rows: list[tuple[str, str]], header: tuple[str, str], output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(4.2, 0.6 + 0.32 * (len(rows) + 1)))
    ax.axis("off")
    table = ax.table(
        cellText=[list(header), *[list(row) for row in rows]],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.35)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_text_pdf(output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.axis("off")
    ax.text(0.05, 0.5, "Just some notes.\nNo table here.", fontsize=11)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    make_table_pdf(
        rows=[
            ("Inception", "5"),
            ("Interstellar", "4.5"),
            ("The Dark Knight", "5"),
            ("Titanic", "4"),
            ("The Matrix", "4.5"),
        ],
        header=("Movie", "Rating"),
        output_path=os.path.join(FIXTURES_DIR, "watched_table.pdf"),
    )

    make_table_pdf(
        rows=[
            ("Avatar", "4.5"),
            ("Deadpool", "4.0"),
        ],
        header=("Movie", "Rating"),
        output_path=os.path.join(FIXTURES_DIR, "watched_table_small.pdf"),
    )

    make_text_pdf(os.path.join(FIXTURES_DIR, "no_table.pdf"))
    print(f"Sample PDFs written to {FIXTURES_DIR}")


if __name__ == "__main__":
    sys.exit(main())
