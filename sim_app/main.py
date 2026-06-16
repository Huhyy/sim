"""Streamlit application entrypoint.

The legacy app still lives in the root-level ``app.py`` during the migration.
This module exists so the final root ``app.py`` can eventually become a thin
``run()`` call after page modules have been extracted.
"""


def run():
    import app  # noqa: F401

