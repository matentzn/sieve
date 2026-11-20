"""Generate the Pydantic datamodel from the SIEVE profile.

The SEPIO core is imported unchanged, and its ``Activity.date`` slot has range
``date``. In the generated code a field named ``date`` shadows the ``datetime.date``
type inside the class body, so ``Optional[date]`` cannot be evaluated on Python 3.10.
Rather than patching the vendored core, the generated code refers to the type
through an alias.

The core's ``type`` slot is a type designator, so every slot whose range is a core
class becomes a union of all its subclasses, profile classes included. Pydantic
builds the schemas of these mutually recursive models depth-first, which needs more
than Python's default recursion limit of 1000. The generated module raises the
limit before the models are built.

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


RECURSION_LIMIT = (
    "# Building the schemas of the mutually recursive models below needs more than the\n"
    "# default recursion limit (sieve.datamodel.codegen).\n"
    "sys.setrecursionlimit(max(sys.getrecursionlimit(), 5000))\n"
)


def raise_recursion_limit(code: str) -> str:
    """Raise the recursion limit right after the generated module imports ``sys``.

    >>> raise_recursion_limit("import re\\nimport sys\\nx = 1\\n").splitlines()[-2]
    'sys.setrecursionlimit(max(sys.getrecursionlimit(), 5000))'
    """
    return code.replace("import sys\n", "import sys\n" + RECURSION_LIMIT, 1)


def generate_pydantic(schema_path: str | Path) -> str:
    """Return the Pydantic module source for ``schema_path``."""
    return raise_recursion_limit(fix_date_shadowing(PydanticGenerator(str(schema_path)).serialize()))


def main() -> None:
    """Write the generated module to the path given as second argument."""
    Path(sys.argv[2]).write_text(generate_pydantic(sys.argv[1]))


if __name__ == "__main__":
    main()
