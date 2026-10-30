"""Generate the Pydantic datamodel from the SIEVE profile.

The SEPIO core is imported unchanged, and its ``Activity.date`` slot has range
``date``. In the generated code a field named ``date`` shadows the ``datetime.date``
type inside the class body, so ``Optional[date]`` cannot be evaluated on Python 3.10.
Rather than patching the vendored core, the generated code refers to the type
through an alias.

Usage::

    uv run python -m sieve.datamodel.codegen schema/sieve.yaml src/sieve/datamodel/sieve_models.py
"""

import re
import sys
from pathlib import Path

from linkml.generators.pydanticgen import PydanticGenerator

DATE_ALIAS_IMPORT = "from datetime import date as _Date\n"


def fix_date_shadowing(code: str) -> str:
    """Refer to the ``date`` type via ``_Date`` so a ``date`` field cannot shadow it.

    >>> fix_date_shadowing("import re\\nx: Optional[date] = None\\ndate: date = Field(...)\\n")
    'import re\\nfrom datetime import date as _Date\\nx: Optional[_Date] = None\\ndate: _Date = Field(...)\\n'
    """
    code = code.replace("Optional[date]", "Optional[_Date]").replace("list[date]", "list[_Date]")
    code = re.sub(r"(\w: )date( = Field)", r"\1_Date\2", code)
    return code.replace("import re\n", "import re\n" + DATE_ALIAS_IMPORT, 1)


def generate_pydantic(schema_path: str | Path) -> str:
    """Return the Pydantic module source for ``schema_path``."""
    return fix_date_shadowing(PydanticGenerator(str(schema_path)).serialize())


def main() -> None:
    """Write the generated module to the path given as second argument."""
    Path(sys.argv[2]).write_text(generate_pydantic(sys.argv[1]))


if __name__ == "__main__":
    main()
