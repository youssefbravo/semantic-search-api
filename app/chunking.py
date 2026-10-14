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
    return AutoTokenizer.from_pretrained(settings.embedding_model_name,
                                        revision=settings.embedding_model_revision)


def count_tokens(text: str) -> int:
    # add_special_tokens=False: count *content* tokens only. The model adds [CLS]/[SEP]
    # at encode time. Passage budgets reserve those special tokens separately;
    # the embedding module checks query lengths including the instruction prefix.
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
    dumps, code). Split using tokenizer offsets and verify source text, including unbroken strings."""
    # Offsets preserve the uploaded text's case and punctuation. Decoding token
    # IDs can lowercase text or expose WordPiece continuation markers.
    offsets = _tokenizer()(sentence, add_special_tokens=False,
                           return_offsets_mapping=True)["offset_mapping"]
    out: list[str] = []
    cursor = 0
    index = 0
    while index < len(offsets):
        end = offsets[min(index + max_tokens, len(offsets)) - 1][1]
        # Starting inside a word can change tokenization. Verify the actual slice.
        while end > cursor and count_tokens(sentence[cursor:end]) > max_tokens:
            end -= 1
        if end <= cursor:
            raise ValueError("Token budget cannot fit a source-text character")
        piece = sentence[cursor:end].strip()
        if piece:
            out.append(piece)
        cursor = end
        while index < len(offsets) and offsets[index][1] <= cursor:
            index += 1
    if sentence[cursor:].strip():
        out.append(sentence[cursor:].strip())
    return out


def chunk_text(
    text: str,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[TextChunk]:
    """Recursive, token-aware chunking with sentence-level overlap.

    Why this strategy (defensible in interviews):
      * Recursive split (paragraph -> sentence -> tokenizer offsets) keeps each chunk
        semantically coherent instead of cutting mid-thought. Coherent chunks
        produce cleaner embeddings and better recall.
      * Token-aware (not character-aware): the model's truncation limit is in
        TOKENS, so we pack to a token budget, not a char budget.
      * ~400-token target leaves headroom under the 512 cap; too-large chunks
        average multiple topics into one vague vector, too-small chunks lose context.
      * ~60-token overlap means a fact split across a boundary stays retrievable
        from the following chunk, at only ~15% extra storage.

    max_tokens / overlap_tokens are parameters (not hardcoded) so the benchmark in
    development probes can compare them; a small authored sweep is not proof of a universal optimum.
    """
    max_tokens = settings.chunk_max_tokens if max_tokens is None else max_tokens
    overlap_tokens = settings.chunk_overlap_tokens if overlap_tokens is None else overlap_tokens
    content_limit = _tokenizer().model_max_length - _tokenizer().num_special_tokens_to_add()
    if max_tokens <= 0 or max_tokens > content_limit:
        raise ValueError(f"max_tokens must be between 1 and {content_limit}")
    if not 0 <= overlap_tokens < max_tokens:
        raise ValueError("overlap_tokens must be nonnegative and smaller than max_tokens")

    units: list[str] = []
    for para in _split_paragraphs(text):
        for sent in _split_sentences(para):
            units.extend(_hard_split(sent, max_tokens) if count_tokens(sent) > max_tokens else [sent])

    chunks: list[TextChunk] = []
    cur: list[str] = []
    for unit in units:
        if cur and count_tokens(" ".join([*cur, unit])) > max_tokens:
            joined = " ".join(cur)
            chunks.append(TextChunk(joined, count_tokens(joined)))
            overlap: list[str] = []
            for sentence in reversed(cur):
                candidate = [sentence, *overlap]
                if count_tokens(" ".join(candidate)) > overlap_tokens:
                    break
                overlap = candidate
            # Incoming units may consume the entire budget; shrink the overlap.
            while overlap and count_tokens(" ".join([*overlap, unit])) > max_tokens:
                overlap.pop(0)
            cur = overlap
        cur.append(unit)
    if cur:
        joined = " ".join(cur)
        chunks.append(TextChunk(joined, count_tokens(joined)))
    return chunks
