"""Apollo.io: find people (free search) and reveal their work emails (uses credits)."""
import time

import requests

BASE_URL = "https://api.apollo.io/api/v1"


class Apollo:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        })

    def _post(self, path, body):
        for attempt in range(4):
            resp = self.session.post(f"{BASE_URL}{path}", json=body, timeout=60)
            if resp.status_code == 429:  # rate limited: wait and retry
                time.sleep(2 ** attempt * 5)
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()

    def search_people(self, filters):
        """Yield people matching the ICP filters. Free, but no emails yet."""
        per_page = filters.get("per_page", 25)
        query = {k: v for k, v in filters.items() if k not in ("per_page", "max_pages")}
        for page in range(1, filters.get("max_pages", 1) + 1):
            data = self._post("/mixed_people/api_search", {**query, "page": page, "per_page": per_page})
            people = data.get("people", [])
            yield from people
            if len(people) < per_page:
                break

    def enrich(self, person_ids):
        """Reveal emails and company details, 10 people per call. Costs Apollo credits."""
        results = []
        for i in range(0, len(person_ids), 10):
            batch = [{"id": pid} for pid in person_ids[i:i + 10]]
            data = self._post("/people/bulk_match", {"details": batch, "reveal_personal_emails": False})
            results.extend(m for m in data.get("matches", []) if m)
        return results


def to_lead(person):
    """Flatten an Apollo person record into the fields the rest of the pipeline uses."""
    org = person.get("organization") or {}
    return {
        "apollo_id": person.get("id", ""),
        "first_name": person.get("first_name", ""),
        "last_name": person.get("last_name", ""),
        "email": person.get("email") or "",
        "email_status": person.get("email_status") or "",
        "title": person.get("title") or "",
        "company": org.get("name") or "",
        "industry": org.get("industry") or "",
        "employees": org.get("estimated_num_employees") or 0,
        "website": org.get("website_url") or "",
        "city": person.get("city") or org.get("city") or "",
        "linkedin": person.get("linkedin_url") or "",
    }
