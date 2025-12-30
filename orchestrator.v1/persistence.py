import json
from pathlib import Path

class JSONLPersistence:
    def __init__(self, path="runs.jsonl"):
        self.path = Path(path)

    def save_round(self, outputs):
        with self.path.open("a") as f:
            f.write(json.dumps(outputs) + "\n")

