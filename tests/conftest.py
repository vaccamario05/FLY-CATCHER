"""Pytest configuration for ADS-B Secure tests."""

import sys
import os

# Ensure project root is in path for all test imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Test-only credentials — web/auth.py has no hardcoded fallback (CWE-259),
# so tests must supply explicit env-based passwords before web.auth is imported.
os.environ.setdefault("OPERATOR_PASSWORD", "operator123")
os.environ.setdefault("SUPERVISOR_PASSWORD", "supervisor123")
os.environ.setdefault("ANALYST_PASSWORD", "analyst123")
