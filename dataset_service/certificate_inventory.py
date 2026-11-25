"""Passive certificate observations for operator-configured domains."""
import ipaddress
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException

MAX_BYTES = 8 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def hostname(value):
    name = value.removesuffix(".").lower()
    if not value.isascii() or len(name) > 253:
        return None
    try:
        ipaddress.ip_address(name)
    except ValueError:
        labels = name.split(".")
        if all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
            return name
    return None


def timestamp(value):
    if value is None:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat()


def observations(rows, domain, retrieved):
    if not isinstance(rows, list):
        raise ValueError("expected an array")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int or not isinstance(row.get("name_value"), str):
            raise ValueError("invalid certificate row")
        dates = {key: timestamp(row.get(field)) for key, field in (
            ("logged_at", "entry_timestamp"), ("not_before", "not_before"), ("not_after", "not_after"))}
        for raw in row["name_value"].splitlines():
            base = hostname(raw.removeprefix("*."))
            if base and (base == domain or base.endswith("." + domain)):
                name = "*." + base if raw.startswith("*.") else base
                result[row["id"], name] = dict(configured_domain=domain, name=name, source="crt.sh",
                    certificate_id=str(row["id"]), retrieved_at=retrieved, **dates)
    return list(result.values())


def fetch_rows(domain):
    query = urlencode({"q": "%." + domain, "output": "json"})
    with httpx.stream("GET", "https://crt.sh/?" + query, timeout=20, follow_redirects=False) as response:
        response.raise_for_status()
        body = bytearray()
        for chunk in response.iter_bytes(chunk_size=65536):
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ValueError("oversized response")
    return json.loads(body)


def inventory_router(path, configured, fetch=fetch_rows):
    router = APIRouter(prefix="/datasets/certificate-inventory")
    domains = set()
    for item in filter(None, (s.strip() for s in configured.split(","))):
        domain = hostname(item)
        if not domain or "." not in domain:
            raise ValueError("invalid inventory domain")
        domains.add(domain)
    locks = {domain: Lock() for domain in domains}

    def check(domain):
        if domain not in domains:
            raise HTTPException(404, "Domain is not configured")

    def connect():
        db = sqlite3.connect(path, timeout=10)
        db.execute("CREATE TABLE IF NOT EXISTS certificate_inventory "
                   "(domain TEXT PRIMARY KEY, outcome TEXT, attempted TEXT, completed TEXT, records TEXT)")
        return db

    @router.get("")
    def list_domains():
        return {"domains": sorted(domains)}

    @router.get("/{domain}")
    def snapshot(domain: str):
        check(domain)
        with closing(connect()) as db:
            row = db.execute("SELECT outcome, attempted, completed, records FROM certificate_inventory WHERE domain=?",
                             (domain,)).fetchone()
        outcome, attempted, completed, records = row or ("never_refreshed", None, None, None)
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(completed)).total_seconds() if completed else None
        return dict(domain=domain, source="crt.sh", last_outcome=outcome, attempted_at=attempted,
                    completed_at=completed, age_seconds=int(age) if age is not None else None,
                    observations=json.loads(records) if records is not None else None)

    @router.post("/{domain}/refresh")
    def refresh(domain: str):
        check(domain)
        if not locks[domain].acquire(blocking=False):
            raise HTTPException(409, "Refresh already running")
        try:
            attempted = now()
            completed = records = None
            try:
                data = fetch(domain)
                records = json.dumps(observations(data, domain, now()))
                completed = now()
                outcome = "success"
            except httpx.HTTPError:
                outcome = "provider_failure"
            except (ValueError, TypeError, AttributeError, OverflowError):
                outcome = "invalid_response"
            with closing(connect()) as db, db:
                db.execute("INSERT INTO certificate_inventory VALUES (?,?,?,?,?) ON CONFLICT(domain) DO UPDATE SET "
                           "outcome=excluded.outcome, attempted=excluded.attempted, "
                           "completed=COALESCE(excluded.completed,completed), records=COALESCE(excluded.records,records)",
                           (domain, outcome, attempted, completed, records))
            return snapshot(domain)
        finally:
            locks[domain].release()

    return router
