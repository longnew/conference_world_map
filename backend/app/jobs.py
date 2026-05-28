from __future__ import annotations

"""Crawler and refresh job entry points."""

from .importers import import_sources


def refresh_ranking_sources() -> None:
    import_sources()


def discover_official_websites() -> None:
    raise NotImplementedError("Website discovery is not implemented yet.")


def extract_event_details() -> None:
    raise NotImplementedError("LLM-assisted official-site extraction is not implemented yet.")


def archive_completed_instances() -> None:
    raise NotImplementedError("Archive job is not implemented yet.")
