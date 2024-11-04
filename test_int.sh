#!/usr/bin/env bash

# Run unit tests.

pytest -s --tb=short --cov-report html:htmlcov/int --cov=src --cov=tests_int tests_int

open htmlcov/int/index.html
