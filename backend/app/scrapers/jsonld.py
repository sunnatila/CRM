"""Shared helper: both goldenpages.uz and yellowpages.uz embed a schema.org
LocalBusiness block (as JSON-LD) on their company detail pages. Both adapters'
normalize() step reads from this same shape, so the extraction lives once here
instead of being reimplemented per adapter.
"""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup


def _iter_jsonld_nodes(payload: Any) -> list[dict]:
    """Flatten a JSON-LD payload (single object, list, or an @graph) into a flat node list."""
    nodes: list[dict] = []
    if isinstance(payload, list):
        for item in payload:
            nodes.extend(_iter_jsonld_nodes(item))
    elif isinstance(payload, dict):
        if "@graph" in payload:
            nodes.extend(_iter_jsonld_nodes(payload["@graph"]))
        else:
            nodes.append(payload)
    return nodes


def extract_local_business(html: str) -> dict | None:
    """Find and return the first schema.org LocalBusiness node in the page's JSON-LD, if any."""
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text()
        if not text or not text.strip():
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        for node in _iter_jsonld_nodes(payload):
            if node.get("@type") == "LocalBusiness":
                return node
    return None
