"""Write a personal subject line, opener and pain point for each lead.

Uses Claude when ANTHROPIC_API_KEY is set; otherwise falls back to
industry templates so the pipeline still works without it.
"""
import json
import os

MODEL = "claude-opus-5-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "first_line": {"type": "string"},
        "pain_point": {"type": "string"},
    },
    "required": ["subject", "first_line", "pain_point"],
    "additionalProperties": False,
}

SYSTEM = """You write the first lines of cold emails for a B2B sales team.
Rules:
- subject: max 6 words, lowercase, no clickbait, no emojis.
- first_line: one sentence, max 25 words, specific to this person's company and role.
  Never invent facts (awards, funding, reviews). Only use the details provided.
- pain_point: one short phrase naming the phone/call problem their business type likely has.
- Plain, friendly tone. No "I hope this email finds you well"."""

TEMPLATES = {
    "dental": "patients calling after hours to book or reschedule",
    "medical": "front desk stuck on the phone instead of with patients",
    "real estate": "buyer enquiries going to voicemail during showings",
    "hvac": "emergency service calls missed after hours",
    "plumbing": "urgent jobs lost when nobody picks up",
    "legal": "potential clients hanging up before intake",
    "law": "potential clients hanging up before intake",
    "insurance": "quote requests waiting on hold",
    "automotive": "service bookings tying up the front desk",
}


def _template(lead):
    industry = lead["industry"].lower()
    pain = next((p for key, p in TEMPLATES.items() if key in industry), "missed calls when the team is busy")
    company = lead["company"] or "your team"
    return {
        "subject": f"missed calls at {company}".lower(),
        "first_line": f"Quick one for you as {lead['title'] or 'a leader'} at {company}: I'd guess the phone rarely stops ringing.",
        "pain_point": pain,
    }


class Personalizer:
    def __init__(self, product):
        self.product = product
        self.client = None
        if os.getenv("ANTHROPIC_API_KEY"):
            import anthropic
            self.client = anthropic.Anthropic()

    def write(self, lead):
        if not self.client:
            return _template(lead)
        try:
            return self._claude(lead)
        except Exception as exc:  # any API problem: fall back rather than stop the run
            print(f"  ! Claude failed for {lead['email']} ({exc}); using template")
            return _template(lead)

    def _claude(self, lead):
        facts = {k: lead[k] for k in ("first_name", "title", "company", "industry", "employees", "city", "website")}
        prompt = (
            f"We sell {self.product['name']}: {self.product['one_liner']}.\n"
            f"Write the personalised parts of a cold email to this lead:\n{json.dumps(facts, indent=2)}"
        )
        response = self.client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            return _template(lead)
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)
