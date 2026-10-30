"""Extract the Mondo requirements workbook into a flat, diffable TSV.

The workbook (sepio-linkml ``docs/requirements-collection/projects/mondo/
Mondo_Requirements_Collection_Forms.xlsx``) is the source of truth. This script
turns its response rows into ``requirements/mondo_requirements.tsv`` so the
traceability tests can run without the workbook. Category / grouping rows
(``EI.CAT.*``) and section-header rows are skipped: they are not responses.

Usage::

    uv run python scripts/extract_requirements.py PATH/TO/Mondo_Requirements_Collection_Forms.xlsx
"""

import csv
import re
import sys
from pathlib import Path

import openpyxl

OUT = Path(__file__).resolve().parent.parent / "requirements" / "mondo_requirements.tsv"
FIELDS = ["id", "form", "title", "current", "desired", "explanation"]
ID_PATTERN = re.compile(r"^(C\d{3}|[A-Z]+\.[A-Z0-9_.]+)$")


def _clean(value: object) -> str:
    """Flatten a cell to a single-line string.

    >>> _clean("a\\n b ")
    'a b'
    >>> _clean(None)
    ''
    """
    if value is None:
        return ""
    return " ".join(str(value).split())


def _row(form: str, cells: tuple, title: str, current: int | None, desired: int | None, explanation: int) -> dict:
    """Build one TSV row from worksheet cells and column indexes."""
    return {
        "id": _clean(cells[0]) if form != "CEM" else _clean(cells[8]),
        "form": form,
        "title": title,
        "current": _clean(cells[current]) if current is not None else "",
        # CT and CEM rows have no desired column: every listed claim type / matrix row is desired.
        "desired": _clean(cells[desired]) if desired is not None else "Y",
        "explanation": _clean(cells[explanation]),
    }


def extract(workbook: Path) -> list[dict]:
    """Return the response rows of every form, in workbook order."""
    wb = openpyxl.load_workbook(workbook, data_only=True)
    rows: list[dict] = []
    for ws in wb:
        form = ws.title.split(" ")[0]
        for cells in ws.iter_rows(values_only=True):
            cells = tuple(cells) + (None,) * 16
            key = _clean(cells[8]) if form == "CEM" else _clean(cells[0])
            if not ID_PATTERN.match(key) or key.startswith("EI.CAT."):
                continue
            if form == "CT":
                rows.append(_row(form, cells, _clean(cells[1]), None, None, 7))
            elif form in ("CRS", "RCS", "EINT"):
                expl = 6 if form == "EINT" else 7
                cur, des = (4, 5) if form == "EINT" else (5, 6)
                rows.append(_row(form, cells, _clean(cells[1]), cur, des, expl))
            elif form == "EIT":
                rows.append(_row(form, cells, _clean(cells[1]), 4, 5, 13))
            elif form == "PROV":
                title = f"{_clean(cells[1])}: {_clean(cells[2])}"
                rows.append(_row(form, cells, title, 6, 7, 9))
            elif form == "CEM":
                rows.append(_row(form, cells, _clean(cells[0]), None, None, 9))
    return rows


def main() -> None:
    """Write the TSV next to the traceability file."""
    rows = extract(Path(sys.argv[1]))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} requirements to {OUT}")


if __name__ == "__main__":
    main()
