#!/usr/bin/env bash

# Run unit tests.

pytest -s --tb=short --cov-report html:htmlcov/tests --cov=src --cov=tests tests

open htmlcov/tests/index.html
