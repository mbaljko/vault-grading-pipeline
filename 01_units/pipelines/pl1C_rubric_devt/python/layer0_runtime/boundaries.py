"""Boundary and marker utilities for registry-driven Layer 0 extraction.

This module operationalizes stop markers declared in operator specs, including
lexical anchors (for example through/shaping/by), clause boundaries, comma-based
boundaries, subordinate extensions, and sentence boundaries.
"""

from __future__ import annotations

import re


def find_anchor_occurrences(text: str, anchor_patterns: list[str]) -> list[tuple[int, int, str]]:
	occurrences: list[tuple[int, int, str]] = []
	for pattern in anchor_patterns:
		if not pattern.strip():
			continue
		compiled = re.compile(rf"(?<!\w){re.escape(pattern)}(?!\w)", flags=re.IGNORECASE)
		for match in compiled.finditer(text):
			occurrences.append((match.start(), match.end(), pattern))
	occurrences.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2].lower()))
	return occurrences


def trim_span(text: str) -> str:
	trimmed = text.strip()
	trimmed = trimmed.strip(" \t\n\r,;:.!?-–—")
	trimmed = re.sub(r"\s+", " ", trimmed)
	return trimmed


def detect_clause_boundary(text: str, start_index: int) -> int | None:
	punctuation_match = re.search(r"[,;:]", text[start_index:])
	conjunction_match = re.search(r"\b(and|but|or|yet|so)\b", text[start_index:], flags=re.IGNORECASE)
	subordinate_match = re.search(
		r"\b(which|that|because|while|when|although|though|who|where|since|as|whereas|unless)\b",
		text[start_index:],
		flags=re.IGNORECASE,
	)
	candidates = []
	if punctuation_match is not None:
		candidates.append(start_index + punctuation_match.start())
	if conjunction_match is not None:
		candidates.append(start_index + conjunction_match.start())
	if subordinate_match is not None:
		candidates.append(start_index + subordinate_match.start())
	return min(candidates) if candidates else None


def detect_subordinate_extension(text: str, start_index: int) -> int | None:
	match = re.search(
		r"\b(which|that|because|while|when|although|though|who|where|since|as|whereas|unless)\b",
		text[start_index:],
		flags=re.IGNORECASE,
	)
	if match is None:
		return None
	return start_index + match.start()


def _find_sentence_end(text: str, start_index: int) -> int | None:
	match = re.search(r"[.!?]", text[start_index:])
	if match is None:
		return None
	return start_index + match.start()


def _find_sentence_start(text: str, start_index: int) -> int | None:
	match = re.search(r"[.!?]\s+", text[start_index:])
	if match is None:
		return None
	return start_index + match.end()


def _find_token_marker(text: str, start_index: int, marker: str) -> int | None:
	match = re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", text[start_index:], flags=re.IGNORECASE)
	if match is None:
		return None
	return start_index + match.start()


def _find_comma_new_clause(text: str, start_index: int) -> int | None:
	for match in re.finditer(r",", text[start_index:]):
		comma_index = start_index + match.start()
		remainder = text[comma_index + 1:]
		if re.match(
			r"\s*(?:and|but|or|yet|so|which|that|because|while|when|although|though|who|where|since|as|whereas|unless|then|therefore|thus|however|directly)\b",
			remainder,
			flags=re.IGNORECASE,
		):
			return comma_index
		if re.match(r"\s*[A-Za-z][A-Za-z\-']*ing\b", remainder, flags=re.IGNORECASE):
			return comma_index
		if re.match(r"\s*[A-Z][a-z]", remainder):
			return comma_index
	return None


def find_first_stop_marker(text: str, start_index: int, stop_markers: list[str]) -> int | None:
	candidates: list[int] = []
	for marker in stop_markers:
		if marker == "comma":
			index = text.find(",", start_index)
			if index != -1:
				candidates.append(index)
		elif marker == "clause_boundary":
			index = detect_clause_boundary(text, start_index)
			if index is not None:
				candidates.append(index)
		elif marker == "subordinate_extension":
			index = detect_subordinate_extension(text, start_index)
			if index is not None:
				candidates.append(index)
		elif marker == "comma_new_clause":
			index = _find_comma_new_clause(text, start_index)
			if index is not None:
				candidates.append(index)
		elif marker == "sentence_end":
			index = _find_sentence_end(text, start_index)
			if index is not None:
				candidates.append(index)
		elif marker == "sentence_start":
			index = _find_sentence_start(text, start_index)
			if index is not None:
				candidates.append(index)
		elif marker in {
			"through",
			"shaping",
			"by",
			"to",
			"which",
			"that",
			"who",
			"where",
			"within",
			"during",
			"at",
			"for",
			"before",
		}:
			index = _find_token_marker(text, start_index, marker)
			if index is not None:
				candidates.append(index)
	return min(candidates) if candidates else None


def find_left_boundary(text: str, anchor_start: int, stop_markers: list[str]) -> int:
	boundary_candidates = [0]
	left_text = text[:anchor_start]
	if "comma" in stop_markers:
		index = left_text.rfind(",")
		if index != -1:
			boundary_candidates.append(index + 1)
	if "sentence_start" in stop_markers:
		matches = list(re.finditer(r"[.!?]", left_text))
		if matches:
			boundary_candidates.append(matches[-1].end())
	if "conjunction_boundary" in stop_markers:
		matches = list(re.finditer(r"\b(and|but|or|yet|so)\b", left_text, flags=re.IGNORECASE))
		if matches:
			boundary_candidates.append(matches[-1].end())
	return max(boundary_candidates)