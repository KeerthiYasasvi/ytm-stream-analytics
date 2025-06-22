#!/usr/bin/env python3
"""
simulator.py

- Fetches your YouTube Music listening history (via ytmusicapi),
- Publishes any *new* plays to Kafka on `listening_events`.
- Persists a local `state.json` so you don’t re-publish old events.
"""

import os, json, time
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ytmusicapi import YTMusic
from kafka import KafkaProducer, errors

# ─── Config & Paths ────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
AUTH_FILE  = HERE / "browser.json"              # your YTM auth token
STATE_FILE = HERE / "state.json"                # stores last timestamp
TOPIC      = os.getenv("KAFKA_TOPIC", "listening_events")
BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
FETCH_LIMIT = int(os.getenv("SIM_FETCH_LIMIT", "50"))
POLL_SEC    = float(os.getenv("SIM_POLL_SECONDS", "60"))

# ─── Helpers ───────────────────────────────────────────────────────────────────
def make_producer(retries=10, delay=2.0):
    """Retry until Kafka’s up, then return a producer."""
    for _ in range(retries):
        try:
            return KafkaProducer(
                bootstrap_servers=BOOTSTRAP.split(","),
                value_serializer=lambda v: json.dumps(v).encode(),
                key_serializer=lambda k: k.encode(),
            )
        except errors.NoBrokersAvailable:
            time.sleep(delay)
    raise RuntimeError("Cannot connect to Kafka")

def load_state():
    """Read last timestamp from state.json, or None if missing/invalid."""
    if os.getenv("SIMULATOR_FORCE_RESET", "").lower() in ("1", "true"):
        return None
    try:
        data = json.loads(STATE_FILE.read_text())
        return datetime.fromisoformat(data["last_ts"])
    except Exception:
        return None

def save_state(ts: datetime):
    """Persist the last‐seen timestamp."""
    try:
        STATE_FILE.write_text(json.dumps({"last_ts": ts.isoformat()}))
    except Exception as e:
        print(f"[simulator][warn] could not write state: {e}")

def parse_ts(ev):
    """Extract an ISO‐format time and return a UTC datetime."""
    raw = ev.get("time") or ev.get("videoAddedTime") or ev.get("timestamp")
    if not raw:
        return datetime.now(timezone.utc)
    # YouTube returns e.g. "2025-06-20T17:06:29.843392Z"
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))

def transform(ev, user_id="user_1"):
    """Map a YTMusic entry into your Kafka message schema."""
    ts_utc   = parse_ts(ev)
    ts_local = ts_utc.astimezone(ZoneInfo("America/New_York"))
    artist   = ev.get("artists", [{}])[0]

    msg = {
        "user_id": user_id,
        "track_id": ev.get("videoId"),
        "artist_id": artist.get("artistId"),
        "timestamp": ts_local.isoformat(),
        "duration_ms": None,
        "metadata": {
            "title": ev.get("title"),
            "album": ev.get("album"),
            "artist_name": artist.get("name"),
        },
    }

    # Enrich duration & release_date from song metadata
    try:
        meta = transform.yt.get_song(ev.get("videoId"))
        length_s = int(meta["microformat"].get("lengthSeconds", 0))
        msg["duration_ms"] = length_s * 1000
        msg["metadata"]["release_date"] = meta["microformat"].get("releaseDate")
    except Exception as e:
        print(f"[simulator][warn] get_song failed: {e}")

    return msg

# ─── Main Loop ────────────────────────────────────────────────────────────────
def main_loop():
    print("🔄 Starting simulator…")
    producer = make_producer()

    # load your YTMusic auth once
    yt = YTMusic(str(AUTH_FILE))
    transform.yt = yt   # stash for use in `transform()`

    last_ts = load_state()
    print(f"▶ Resuming from {last_ts!r}")

    while True:
        recent = yt.get_history()[:FETCH_LIMIT]
        new    = []

        for ev in recent:
            ev_ts = parse_ts(ev)
            if last_ts is None or ev_ts > last_ts:
                new.append((ev_ts, ev))
        new.sort(key=lambda x: x[0])  # oldest→newest

        if new:
            print(f"⬆️  Publishing {len(new)} new events…")
            for ev_ts, ev in new:
                msg = transform(ev)
                key = f"{msg['user_id']}-{msg['timestamp']}"
                producer.send(TOPIC, key=key, value=msg)
                last_ts = ev_ts
            producer.flush()
            save_state(last_ts)
        else:
            print("– no new events")

        time.sleep(POLL_SEC)

if __name__ == "__main__":
    main_loop()
