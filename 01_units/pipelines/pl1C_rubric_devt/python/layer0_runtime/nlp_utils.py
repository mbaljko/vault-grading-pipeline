from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

try:
	import spacy  # type: ignore
except ImportError:  # pragma: no cover
	spacy = None


_NLP = None


@dataclass(frozen=True)
class _FallbackDoc:
	text: str


def _get_nlp() -> Any:
	global _NLP
	if _NLP is not None:
		return _NLP
	if spacy is None:
		return None
	for model_name in ["en_core_web_sm", "en_core_web_md"]:
		try:
			_NLP = spacy.load(model_name)
			return _NLP
		except OSError:
			continue
	return None


@lru_cache(maxsize=256)
def parse_text(text: str):
	nlp = _get_nlp()
	if nlp is None:
		return _FallbackDoc(text)
	return nlp(text)


def noun_chunks_with_offsets(doc) -> list[tuple[int, int, str]]:
	if doc is None or not hasattr(doc, "noun_chunks"):
		return []
	chunks: list[tuple[int, int, str]] = []
	for chunk in doc.noun_chunks:
		chunks.append((chunk.start_char, chunk.end_char, chunk.text))
	return chunks


def _fallback_nounish_spans(text: str) -> list[tuple[int, int, str]]:
	spans: list[tuple[int, int, str]] = []
	for match in re.finditer(r"[A-Za-z0-9][A-Za-z0-9\-'/]*(?:\s+[A-Za-z0-9][A-Za-z0-9\-'/]*)*", text):
		candidate = match.group(0).strip()
		if candidate:
			spans.append((match.start(), match.end(), candidate))
	return spans


def nearest_left_noun_chunk(doc, anchor_start: int, minimum_start: int = 0) -> tuple[int, int, str] | None:
	chunks = noun_chunks_with_offsets(doc) if doc is not None else []
	eligible = [chunk for chunk in chunks if chunk[1] <= anchor_start and chunk[0] >= minimum_start]
	if eligible:
		return max(eligible, key=lambda chunk: (chunk[1], chunk[0]))
	if doc is None:
		return None
	text = doc.text[minimum_start:anchor_start]
	fallback_spans = _fallback_nounish_spans(text)
	if not fallback_spans:
		return None
	start, end, chunk_text = fallback_spans[-1]
	return (minimum_start + start, minimum_start + end, chunk_text)


def first_right_noun_chunk(doc, anchor_end: int, stop_index: int | None) -> tuple[int, int, str] | None:
	chunks = noun_chunks_with_offsets(doc) if doc is not None else []
	eligible = [
		chunk
		for chunk in chunks
		if chunk[0] >= anchor_end and (stop_index is None or chunk[1] <= stop_index)
	]
	if eligible:
		return min(eligible, key=lambda chunk: (chunk[0], chunk[1]))
	if doc is None:
		return None
	right_limit = stop_index if stop_index is not None else len(doc.text)
	fallback_spans = _fallback_nounish_spans(doc.text[anchor_end:right_limit])
	if not fallback_spans:
		return None
	start, end, chunk_text = fallback_spans[0]
	return (anchor_end + start, anchor_end + end, chunk_text)