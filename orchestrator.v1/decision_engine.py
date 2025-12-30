WEIGHTS = {
    "feasibility": 0.25,
    "differentiation": 0.20,
    "user_value": 0.25,
    "risk_mitigation": 0.20,
    "consistency": 0.10
}

# THRESHOLD
MIN_SCORE = 8.0

def weighted_score(scorecard):
    return sum(scorecard[k] * WEIGHTS[k] for k in WEIGHTS)

def is_winner(scorecard):
    return weighted_score(scorecard) >= MIN_SCORE

