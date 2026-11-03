"""Collectibles inventory pipeline.

Ingest a comic-book inventory CSV into SQLite, classify each book with a
rule-based classifier (plus an optional local-LLM second tier), price it
against comparable sales, and report the result.

Standard library only. The optional dashboard is the single exception and
is guarded so nothing here depends on it.
"""

__version__ = "1.0.0"
