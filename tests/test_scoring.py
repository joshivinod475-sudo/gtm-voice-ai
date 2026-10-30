import unittest
from pathlib import Path

import yaml

from gtm.scoring import rank, score_lead

RULES = yaml.safe_load(Path("config/icp.yaml").read_text(encoding="utf-8"))["scoring"]


def lead(**overrides):
    base = {"industry": "dental clinics", "title": "Owner", "employees": 20,
            "email": "a@b.example", "email_status": "verified", "website": "https://b.example"}
    return {**base, **overrides}


class ScoringTest(unittest.TestCase):
    def test_perfect_fit_scores_100(self):
        self.assertEqual(score_lead(lead(), RULES)[0], 100)

    def test_wrong_industry_and_role_scores_low(self):
        score, _ = score_lead(lead(industry="software", title="Engineer", employees=5000), RULES)
        self.assertLess(score, RULES["min_score"])

    def test_rank_drops_leads_without_email(self):
        self.assertEqual(rank([lead(email="")], RULES), [])

    def test_rank_orders_best_first(self):
        ranked = rank([lead(email_status="guessed"), lead()], RULES)
        self.assertEqual([l["score"] for l in ranked], [100, 90])


if __name__ == "__main__":
    unittest.main()
