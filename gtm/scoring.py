"""Give each lead a 0-100 fit score so we only email the best ones."""


def score_lead(lead, rules):
    score = 0
    reasons = []

    industry = lead["industry"].lower()
    if any(word in industry for word in rules["hot_industries"]):
        score += 35
        reasons.append("call-heavy industry")

    title = lead["title"].lower()
    if any(word in title for word in rules["decision_maker_words"]):
        score += 25
        reasons.append("decision maker")

    low, high = rules["ideal_employees"]
    if low <= (lead["employees"] or 0) <= high:
        score += 20
        reasons.append("right company size")

    if lead["email"] and lead["email_status"] == "verified":
        score += 15
        reasons.append("verified email")
    elif lead["email"]:
        score += 5

    if lead["website"]:
        score += 5

    return score, reasons


def rank(leads, rules):
    """Score every lead, drop weak ones and anyone without an email, best first."""
    kept = []
    for lead in leads:
        lead["score"], reasons = score_lead(lead, rules)
        lead["score_reasons"] = ", ".join(reasons)
        if lead["email"] and lead["score"] >= rules["min_score"]:
            kept.append(lead)
    return sorted(kept, key=lambda l: l["score"], reverse=True)
