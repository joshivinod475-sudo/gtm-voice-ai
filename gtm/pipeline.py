"""The whole GTM run: find -> enrich -> score -> personalise -> export -> push."""
import csv
import json
import os
from datetime import date
from pathlib import Path

from .apollo import Apollo, to_lead
from .personalize import Personalizer
from .saleshandy import Saleshandy
from .scoring import rank

OUTPUT = Path("output")
SEEN_FILE = OUTPUT / "seen.json"
CSV_COLUMNS = ["score", "first_name", "last_name", "email", "title", "company", "industry",
               "employees", "city", "website", "subject", "first_line", "pain_point", "score_reasons"]


def _load_seen():
    return set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()


def _save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def export_csv(leads):
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"leads_{date.today():%Y%m%d}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)
    return path


def personalise_and_export(leads, config):
    writer = Personalizer(config["product"])
    for lead in leads:
        lead.update(writer.write(lead))
        print(f"  {lead['score']:>3}  {lead['first_name']} @ {lead['company']}: {lead['first_line']}")
    return export_csv(leads)


def run(config, live=False, limit=25):
    OUTPUT.mkdir(exist_ok=True)
    seen = _load_seen()

    print("1/5 Searching Apollo for people who match the ICP...")
    apollo = Apollo(os.environ["APOLLO_API_KEY"])
    found = [p for p in apollo.search_people(config["apollo_search"]) if p["id"] not in seen]
    print(f"    {len(found)} new people found")

    print(f"2/5 Revealing emails for up to {limit} of them (uses Apollo credits)...")
    leads = [to_lead(p) for p in apollo.enrich([p["id"] for p in found[:limit]])]

    print("3/5 Scoring leads...")
    leads = rank(leads, config["scoring"])
    print(f"    {len(leads)} leads scored {config['scoring']['min_score']}+")
    if not leads:
        return

    print("4/5 Writing personalised openers...")
    path = personalise_and_export(leads, config)
    print(f"    Saved {path}")

    if not live:
        print("5/5 Dry run: nothing sent to Saleshandy. Check the CSV, then rerun with --live.")
        return

    print("5/5 Adding leads to the Saleshandy sequence...")
    saleshandy = Saleshandy(os.environ["SALESHANDY_API_KEY"])
    results = saleshandy.import_prospects(leads, os.environ["SALESHANDY_STEP_ID"], config["saleshandy"])
    for email, status in results.items():
        print(f"    {email}: {status}")
    seen.update(lead["apollo_id"] for lead in leads)
    _save_seen(seen)


def demo(config):
    """Run scoring + personalisation on made-up sample people. No API keys needed."""
    sample = json.loads(Path("data/sample_people.json").read_text())
    leads = rank([to_lead(p) for p in sample], config["scoring"])
    print(f"Demo: {len(sample)} sample people -> {len(leads)} good leads\n")
    path = personalise_and_export(leads, config)
    print(f"\nSaved {path}")
