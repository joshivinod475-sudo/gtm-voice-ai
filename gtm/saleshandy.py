"""Saleshandy: load prospects into an email sequence step."""
import requests

BASE_URL = "https://open-api.saleshandy.com/v1"

STATUS = {
    10000: "added",
    10100: "invalid email",
    10200: "already in this sequence",
    10600: "duplicate",
    10700: "bounced before",
    10800: "unsubscribed",
    12000: "active in another sequence",
}


class Saleshandy:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key, "Content-Type": "application/json"})

    def _get(self, path):
        resp = self.session.get(f"{BASE_URL}{path}", timeout=60)
        resp.raise_for_status()
        return resp.json()

    def sequences(self):
        return self._get("/sequences")

    def fields(self):
        return self._get("/fields")

    def import_prospects(self, leads, step_id, settings):
        """Add leads to a sequence step. Returns {email: status} for each lead."""
        ids = settings["field_ids"]
        missing = [k for k in ("first_name", "email") if not ids.get(k)]
        if missing:
            raise ValueError(f"Set saleshandy.field_ids {missing} in config/icp.yaml (run: python main.py fields)")

        values = {
            "first_name": "first_name", "last_name": "last_name", "email": "email",
            "company": "company", "job_title": "title", "first_line": "first_line",
            "pain_point": "pain_point",
        }
        prospect_list = []
        for lead in leads:
            fields = [{"id": ids[key], "value": str(lead.get(src, ""))}
                      for key, src in values.items() if ids.get(key)]
            prospect_list.append({"fields": fields})

        results = {}
        for i in range(0, len(prospect_list), 100):
            resp = self.session.post(f"{BASE_URL}/prospects/import", timeout=120, json={
                "prospectList": prospect_list[i:i + 100],
                "stepId": step_id,
                "verifyProspects": settings.get("verify_prospects", True),
                "conflictAction": settings.get("conflict_action", "noUpdate"),
            })
            resp.raise_for_status()
            for row in resp.json().get("payload", []):
                results[row.get("email")] = STATUS.get(row.get("status"), f"status {row.get('status')}")
        return results
