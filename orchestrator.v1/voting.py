from collections import Counter

def majority_vote(decisions):
    counts = Counter(decisions)
    return counts.most_common(1)[0][0]

