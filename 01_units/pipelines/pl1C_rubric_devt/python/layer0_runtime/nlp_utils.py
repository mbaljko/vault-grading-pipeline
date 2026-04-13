from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


_RIGHT_NP_BLOCKING_TOKENS = {
	"and",
	"or",
	"but",
	"to",
	"through",
	"shaping",
	"by",
	"which",
	"that",
	"because",
	"while",
	"when",
	"although",
	"though",
	"who",
	"where",
	"since",
	"as",
	"whereas",
	"unless",
	"directly",
	"then",
}

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


def _leading_nounish_span(text: str) -> tuple[int, int, str] | None:
	first_token = re.search(r"[A-Za-z0-9][A-Za-z0-9\-'/]*", text)
	if first_token is None:
		return None
	start = first_token.start()
	position = start
	end = first_token.end()
	token_count = 0
	while True:
		match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9\-'/]*)", text[position:])
		if match is None:
			break
		token = match.group(1)
		token_start = position + match.start(1)
		token_end = position + match.end(1)
		if token_count > 0 and token.lower() in _RIGHT_NP_BLOCKING_TOKENS:
			break
		end = token_end
		position = token_end
		token_count += 1
	candidate = text[start:end].strip()
	if not candidate:
		return None
	return (start, end, candidate)


def _extend_compact_coordination(text: str, start: int, end: int, right_limit: int) -> tuple[int, int, str]:
	current_end = end
	while current_end < right_limit:
		remainder = text[current_end:right_limit]
		comma_connector = re.match(r"\s*,\s*(?:(?:and|or)\s+)?", remainder, flags=re.IGNORECASE)
		conjunction_connector = re.match(r"\s+(?:and|or)\s+", remainder, flags=re.IGNORECASE)
		connector = None
		if comma_connector is not None and "," in comma_connector.group(0):
			remainder_after_comma = remainder[comma_connector.end():]
			if not re.search(r"(?:,\s*(?:and|or)\s+|\s+(?:and|or)\s+)", remainder_after_comma, flags=re.IGNORECASE):
				break
			connector = comma_connector
		elif conjunction_connector is not None:
			connector = conjunction_connector
		if connector is None:
			break
		item_start = current_end + connector.end()
		item = _leading_nounish_span(text[item_start:right_limit])
		if item is None:
			break
		rel_start, rel_end, _ = item
		if rel_start != 0:
			break
		current_end = item_start + rel_end
	return (start, current_end, text[start:current_end])


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


def first_right_noun_chunk(
	doc,
	anchor_end: int,
	stop_index: int | None,
	*,
	allow_coordination: bool = False,
) -> tuple[int, int, str] | None:
	chunks = noun_chunks_with_offsets(doc) if doc is not None else []
	eligible = [
		chunk
		for chunk in chunks
		if chunk[0] >= anchor_end and (stop_index is None or chunk[1] <= stop_index)
	]
	if eligible:
		chunk_start, chunk_end, chunk_text = min(eligible, key=lambda chunk: (chunk[0], chunk[1]))
		if allow_coordination:
			right_limit = stop_index if stop_index is not None else len(doc.text)
			chunk_start, chunk_end, chunk_text = _extend_compact_coordination(doc.text, chunk_start, chunk_end, right_limit)
		return (chunk_start, chunk_end, chunk_text)
	if doc is None:
		return None
	right_limit = stop_index if stop_index is not None else len(doc.text)
	fallback_span = _leading_nounish_span(doc.text[anchor_end:right_limit])
	if fallback_span is None:
		return None
	start, end, chunk_text = fallback_span
	absolute_start = anchor_end + start
	absolute_end = anchor_end + end
	if allow_coordination:
		absolute_start, absolute_end, chunk_text = _extend_compact_coordination(
			doc.text,
			absolute_start,
			absolute_end,
			right_limit,
		)
	return (absolute_start, absolute_end, chunk_text)