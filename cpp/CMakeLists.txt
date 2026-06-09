# Optional standalone CMake build for the C++ engine.
# The primary build path is setup.py / pip install — this CMakeLists is for
# IDE integration and exercising the C++ code outside of Python.

cmake_minimum_required(VERSION 3.15)
project(options_pricing_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_cpp_engine bindings.cpp)

if(MSVC)
    target_compile_options(_cpp_engine PRIVATE /O2 /EHsc)
else()
    target_compile_options(_cpp_engine PRIVATE -O3 -ffast-math)
endif()
