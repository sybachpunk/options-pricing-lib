"""
pytest bootstrap.

Lets the suite run from a fresh clone with only numpy/scipy/pytest installed,
i.e. WITHOUT `pip install -e .` first. If the package was installed (editable
or otherwise) this is a harmless no-op, since the installed location already
wins on sys.path. We only add the in-repo `src/` as a fallback.
"""
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if SRC.is_dir():
    sys.path.insert(0, str(SRC))
