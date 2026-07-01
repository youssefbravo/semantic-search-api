import re
from dataclasses import dataclass
from functools import lru_cache

from transformers import AutoTokenizer

from .config import get_settings

settings = get_settings()

# Lightweight sentence boundary: split after . ! ? when followed by whitespace and a
# capital/digit. We deliberately avoid nltk/spacy — a regex is good enough for
# chunking and keeps the image small and fully reproducible (no model downloads at
# import time beyond the tokenizer).
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_PARAGRAPH_RE = re.compile(r"\n\s*\n")


@lru_cache
def _tokenizer():
    # Same tokenizer the embedding model uses, so our token counts match what the
    # model actually sees at encode time.
    return AutoTokenizer.from_pretrained(settings.embedding_model_name)


def count_tokens(text: str) -> int:
    # add_special_tokens=False: count *content* tokens only. The model adds [CLS]/[SEP]
    # at encode time, and queries add a prefix — keeping content under max_tokens
    # leaves headroom for both so nothing gets truncated.
    return len(_tokenizer().encode(text, add_special_tokens=False))


@dataclass
class TextChunk:
    content: str
    token_count: int


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_RE.split(text) if p.strip()]


def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(paragraph) if s.strip()]


def _hard_split(sentence: str, max_tokens: int) -> list[str]:
    """Fallback for a single 'sentence' longer than max_tokens (table rows, URL
    dumps, code). Split on words to guarantee no unit ever exceeds the cap."""
    words = sentence.split()
    out: list[str] = []
    cur: list[str] = []
    for w in words:
        cur.append(w)
        if count_tokens(" ".join(cur)) >= max_tokens:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def chunk_text(
    text: str,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[TextChunk]:
    """Recursive, token-aware chunking with sentence-level overlap.

    Why this strategy (defensible in interviews):
      * Recursive split (paragraph -> sentence -> word) keeps each chunk
        semantically coherent instead of cutting mid-thought. Coherent chunks
        produce cleaner embeddings and better recall.
      * Token-aware (not character-aware): the model's truncation limit is in
        TOKENS, so we pack to a token budget, not a char budget.
      * ~400-token target leaves headroom under the 512 cap; too-large chunks
        average multiple topics into one vague vector, too-small chunks lose context.
      * ~60-token overlap means a fact split across a boundary stays retrievable
        from the following chunk, at only ~15% extra storage.

    max_tokens / overlap_tokens are parameters (not hardcoded) so the benchmark in
    phase 4 can sweep them and we can SHOW the chosen value is empirically best.
    """
    max_tokens = max_tokens or settings.chunk_max_tokens
    overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens

    # Flatten to ordered sentence units, each guaranteed <= max_tokens.
    units: list[str] = []
    for para in _split_paragraphs(text):
        for sent in _split_sentences(para):
            if count_tokens(sent) > max_tokens:
                units.extend(_hard_split(sent, max_tokens))
            else:
                units.append(sent)

    chunks: list[TextChunk] = []
    cur: list[str] = []
    cur_tokens = 0

    def emit() -> None:
        if cur:
            joined = " ".join(cur)
            chunks.append(TextChunk(content=joined, token_count=count_tokens(joined)))

    for unit in units:
        ut = count_tokens(unit)
        if cur and cur_tokens + ut > max_tokens:
            emit()
            # Seed the next chunk with trailing sentences summing to ~overlap_tokens.
            overlap: list[str] = []
            otok = 0
            for s in reversed(cur):
                st = count_tokens(s)
                if otok + st > overlap_tokens:
                    break
                overlap.insert(0, s)
                otok += st
            cur, cur_tokens = overlap, otok
        cur.append(unit)
        cur_tokens += ut

    emit()
    return chunks
