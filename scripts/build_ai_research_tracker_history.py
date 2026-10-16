"""Expand sourced tracker figures into an explicit 2020-2026 venue-year grid."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/ai_research_observatory/tracker_history.json"
VENUES = ROOT / "data/ai_research_observatory/venues.json"
OUTPUT = ROOT / "static/data/ai-research-conference-history.json"
COLORS = ("#b64046", "#227c82", "#ae7228", "#5969ac", "#68813d", "#9b5a8f", "#576974")


def build(source, catalog):
    by_id = {venue["id"]: venue for venue in catalog}
    ids = [venue_id for field in source["fields"] for venue_id in field["venues"]]
    if len(ids) != len(set(ids)) or any(venue_id not in by_id for venue_id in ids):
        raise ValueError("Tracker field IDs must be unique members of the venue catalog")
    known = {(row["venue"], row["year"]): row for row in source["known"]}
    if len(known) != len(source["known"]) or any(key[0] not in ids or not 2020 <= key[1] <= 2026 for key in known):
        raise ValueError("Duplicate or out-of-grid known count")
    not_held = {(entry["venue"], year): entry["source"] for entry in source["not_held"] for year in entry["years"]}
    if any(key in known or key[0] not in ids or not 2020 <= key[1] <= 2026 for key in not_held):
        raise ValueError("Invalid not-held entry")
    conferences = [
        {"id": venue_id, "name": by_id[venue_id]["name"], "color": COLORS[index % len(COLORS)]}
        for field in source["fields"] for index, venue_id in enumerate(field["venues"])
    ]
    counts = []
    for venue_id in ids:
        for year in range(2020, 2027):
            item = known.get((venue_id, year), {})
            submitted, accepted = item.get("submitted"), item.get("accepted")
            if submitted is not None and accepted is not None and accepted > submitted:
                raise ValueError(f"Accepted exceeds submitted: {venue_id} {year}")
            for metric, value in (("submitted", submitted), ("accepted", accepted)):
                if value is not None and (not isinstance(value, int) or value <= 0 or not (item.get(f"{metric}_source") or item.get("source", "")).startswith("https://")):
                    raise ValueError(f"Missing valid organizer source: {venue_id} {year} {metric}")
            status = "not-held" if (venue_id, year) in not_held else "verified" if submitted is not None and accepted is not None else "partial" if submitted is not None or accepted is not None else "unverified"
            counts.append({"venue": venue_id, "year": year, "status": status, "submitted": submitted, "accepted": accepted,
                           "submitted_source": item.get("submitted_source", item.get("source")) if submitted is not None else None,
                           "accepted_source": item.get("accepted_source", item.get("source")) if accepted is not None else None,
                           "scope": item.get("scope", "No comparable organizer figure verified"),
                           "status_source": not_held.get((venue_id, year))})
    return {"reviewed_at": source["reviewed_at"],
            "method": "Organizer-reported figures only. Null is an unverified or unpublished figure, never zero. Acceptance scope can vary between conferences and years; inspect scope before comparing ratios.",
            "fields": source["fields"], "conferences": conferences, "counts": counts, "awards": source["awards"]}


if __name__ == "__main__":
    result = build(json.loads(SOURCE.read_text()), json.loads(VENUES.read_text()))
    OUTPUT.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
    print(f"Wrote {len(result['counts'])} venue-years to {OUTPUT}")
