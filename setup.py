"""
setup.py exists solely to build the optional C++ extension via pybind11.
The pure-Python package is configured in pyproject.toml.

The C++ extension is OPT-IN: install with the environment variable
OPTIONS_PRICING_BUILD_CPP=1 set, e.g.

    # Windows PowerShell
    $env:OPTIONS_PRICING_BUILD_CPP="1"; pip install -e ".[dev,api]"

    # macOS / Linux
    OPTIONS_PRICING_BUILD_CPP=1 pip install -e ".[dev,api]"

Building requires a C++17 compiler (MSVC Build Tools on Windows, gcc/clang
elsewhere). Without the env var, a pure-Python install is performed and
options_pricing.cpp_engine is None.
"""
import os
import sys
from pathlib import Path

from setuptools import setup

ROOT = Path(__file__).parent
CPP_SRC = ROOT / "cpp" / "bindings.cpp"

BUILD_CPP = os.environ.get("OPTIONS_PRICING_BUILD_CPP", "0") == "1"


def get_ext_modules():
    if not BUILD_CPP or not CPP_SRC.exists():
        return []

    # Import pybind11 lazily so an install without OPTIONS_PRICING_BUILD_CPP=1
    # doesn't even need pybind11 present.
    try:
        from pybind11.setup_helpers import Pybind11Extension
    except ImportError:
        print(
            "OPTIONS_PRICING_BUILD_CPP=1 was set but pybind11 isn't installed. "
            "Run: pip install pybind11",
            file=sys.stderr,
        )
        return []

    if sys.platform == "win32":
        extra = ["/O2", "/std:c++17", "/EHsc"]
    else:
        extra = ["-O3", "-std=c++17", "-ffast-math"]

    # setuptools requires forward-slash paths relative to setup.py
    rel_src = "cpp/bindings.cpp"
    return [
        Pybind11Extension(
            "options_pricing._cpp_engine",
            [rel_src],
            cxx_std=17,
            extra_compile_args=extra,
        )
    ]


cmdclass = {}
if BUILD_CPP:
    try:
        from pybind11.setup_helpers import build_ext as pybind11_build_ext
        cmdclass["build_ext"] = pybind11_build_ext
    except ImportError:
        pass

setup(
    ext_modules=get_ext_modules(),
    cmdclass=cmdclass,
)
