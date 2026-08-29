"""Notification and statistics payloads.

Split out of the old `schemas/review.py`, whose review/permission/claim shapes
went away with the v1 endpoints -- the file kept only these, and a module named
after a domain it no longer describes is a trap for the next reader.
"""

from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    message: str
    link: str | None
    read: bool
    created_at: datetime


class OperatorStatsOut(BaseModel):
    id: int
    username: str
    full_name: str
    avatar_url: str | None
    today_count: int
    week_count: int
    total_count: int


class OverviewStatsOut(BaseModel):
    today_filled: int
    week_filled: int
    # v1 counted "requests awaiting an admin". There are no requests now; the
    # number worth watching is how much half-finished work is sitting unclaimed.
    total_companies: int
    finished_leads: int
    active_operators: int
