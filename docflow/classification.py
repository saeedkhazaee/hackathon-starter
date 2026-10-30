"""Reproducible multinomial Naive Bayes, Laplace smoothing, no downloaded model."""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


def tokens(text):
    return re.findall(r"[a-z]+", text.lower())


class Classifier:
    def __init__(self, examples):
        self.words = defaultdict(Counter)
        self.documents = Counter()
        self.vocabulary = set()
        for example in examples:
            label = example["category"]
            words = tokens(example["text"])
            self.words[label].update(words)
            self.documents[label] += 1
            self.vocabulary.update(words)
        self.totals = {label: sum(words.values()) for label, words in self.words.items()}

    def predict(self, text):
        # Business headers, not the possibly very large line-item appendix.
        header = text.split("Items:", 1)[0][:4096]
        counts = Counter(t for t in tokens(header) if t in self.vocabulary)
        if not counts:
            return {"category": "unknown", "confidence": 0.0}
        scores = {}
        for label in sorted(self.documents):
            score = math.log(self.documents[label] / self.documents.total())
            denominator = self.totals[label] + len(self.vocabulary)
            for word, count in counts.items():
                score += count * math.log((self.words[label][word] + 1) / denominator)
            scores[label] = score
        maximum = max(scores.values())
        weights = {label: math.exp(score - maximum) for label, score in scores.items()}
        best = max(weights, key=weights.get)
        return {"category": best, "confidence": round(weights[best] / sum(weights.values()), 6)}


MODEL = Classifier(json.loads((Path(__file__).resolve().parents[1] / "data/classification.json").read_text(encoding="utf-8")))
