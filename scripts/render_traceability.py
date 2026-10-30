"""Write docs/requirements-traceability.md from the schema and the traceability file.

Usage::

    uv run python scripts/render_traceability.py
"""

from sieve.traceability import ROOT, render_markdown

OUT = ROOT / "docs" / "requirements-traceability.md"

if __name__ == "__main__":
    OUT.write_text(render_markdown())
    print(f"wrote {OUT}")
