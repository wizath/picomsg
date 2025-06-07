"""
PicoMsg Test Suite

This test suite is organized into two main categories:

1. Unit Tests (tests/unittest/):
   - test_schema_ast.py: Tests for AST data structures
   - test_schema_parser.py: Tests for schema parsing logic
   - test_binary_format.py: Tests for binary format utilities
   - test_alignment.py: Tests for alignment calculation utilities
   - test_c_codegen.py: Tests for C code generator
   - test_rust_codegen.py: Tests for Rust code generator
   - test_cli.py: Tests for command-line interface

2. Integration Tests (tests/integration/):
   - test_cross_platform.py: Cross-platform compatibility tests
   - test_end_to_end.py: End-to-end workflow tests
   - test_binary_compatibility.py: Binary format compatibility tests
   - test_integration.py: Legacy integration tests

Run all tests with: pytest tests/
Run unit tests only: pytest tests/unittest/
Run integration tests only: pytest tests/integration/
""" 
