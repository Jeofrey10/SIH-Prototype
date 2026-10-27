"""Text normalization for related complaint detection."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no", "nor",
    "so", "yet", "both", "each", "few", "more", "most", "other", "some",
    "such", "than", "too", "very", "just", "also", "about", "after",
    "before", "between", "into", "through", "during", "above", "below",
    "up", "down", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "every", "own", "same", "that", "this", "these", "those", "its", "it",
    "they", "them", "their", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "which", "who", "whom", "what",
    # Domain-specific stopwords
    "institute", "institution", "college", "university", "complaint",
    "complainant", "student", "students", "regarding", "against", "please",
})

DOMAIN_TERMS = frozenset({
    "fee", "refund", "tuition", "hostel", "scholarship", "admission",
    "cancel", "seat", "capitation", "faculty", "salary", "qualification",
    "recruit", "laboratory", "lab", "infrastructure", "library", "building",
    "approval", "affiliation", "extension", "accreditation", "intake",
    "fake", "forged", "certificate", "degree", "exam", "examination",
    "result", "harassment", "ragging", "safety", "placement", "bond",
    "documents", "original", "withheld", "deposit",
})


def stem_word(word: str) -> str:
    """Simple deterministic suffix stemmer."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("sses"):
        return word[:-2]
    for suffix in ("ing", "ment", "ly", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    return word


def normalize_text(text: str) -> tuple[list[str], set[str], Counter]:
    """
    Normalize text for comparison.
    Returns: (token_list, token_set, token_counter)
    """
    # Unicode NFKC normalization, lowercase
    text = unicodedata.normalize("NFKC", text).lower()
    # Replace non-alphanumeric with spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Tokenize
    tokens = text.split()
    # Drop tokens shorter than 3 chars, pure numbers, and stopwords
    tokens = [
        t for t in tokens
        if len(t) >= 3 and not t.isdigit() and t not in STOPWORDS
    ]
    # Stem
    tokens = [stem_word(t) for t in tokens]
    # Filter out any that became too short after stemming
    tokens = [t for t in tokens if len(t) >= 3]

    token_set = set(tokens)
    token_counter = Counter(tokens)

    return tokens, token_set, token_counter


def get_keywords(text: str, max_keywords: int = 15) -> list[str]:
    """Extract top keywords from text."""
    _, _, counter = normalize_text(text)
    # Sort by frequency desc, then alphabetically for ties
    sorted_tokens = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    return [t for t, _ in sorted_tokens[:max_keywords]]


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def cosine_similarity_sublinear_tf(counter_a: Counter, counter_b: Counter) -> float:
    """Compute cosine similarity using sublinear TF (1 + ln(tf))."""
    all_terms = set(counter_a.keys()) | set(counter_b.keys())
    if not all_terms:
        return 0.0

    def sublinear(tf: int) -> float:
        return 1.0 + math.log(tf) if tf > 0 else 0.0

    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for term in all_terms:
        va = sublinear(counter_a.get(term, 0))
        vb = sublinear(counter_b.get(term, 0))
        dot_product += va * vb
        norm_a += va * va
        norm_b += vb * vb

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))
