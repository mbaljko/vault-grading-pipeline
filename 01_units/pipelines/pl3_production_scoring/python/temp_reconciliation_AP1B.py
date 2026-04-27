from __future__ import annotations

import csv
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import math


NOT_YET_COMPONENTISED = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised.csv"
)
MASSAGED_PREV = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged-prev.csv"
)
MASSAGED_OUTPUT = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged.csv"
)
MASSAGED_REPORT = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_reconciliation_report.md"
)

SUBMISSION_LINE_RE = re.compile(r"^\+\+\+\s*submission_id\s*=\s*\d+\s*$", re.IGNORECASE)
PLUS_LINE_RE = re.compile(r"^\+\+\+\s*$")
SUBMISSION_INLINE_RE = re.compile(r"submission_id\s*=\s*\d+", re.IGNORECASE)


def normalize_response_text(text: str) -> str:
    cleaned_lines: list[str] = []
    normalized_newlines = text.replace("\r\n", "\n").replace("\r", "\n")
    for raw_line in normalized_newlines.split("\n"):
        stripped = raw_line.strip()
        if SUBMISSION_LINE_RE.match(stripped):
            continue
        if PLUS_LINE_RE.match(stripped):
            continue
        stripped = SUBMISSION_INLINE_RE.sub("", stripped)
        if stripped:
            cleaned_lines.append(stripped)
    result = re.sub(r"\s+", " ", " ".join(cleaned_lines)).strip().lower()
    return result


def extract_claim_structure(text: str) -> dict[str, any]:
    """Extract structured information from a claim response."""
    normalized = normalize_response_text(text)
    
    # Count claims (look for "claim" keyword)
    claim_count = len(re.findall(r'\bclaim\s+\d+|\bclaim\s+statement', normalized))
    claim_count = max(1, claim_count)  # At least 1 if it looks like a claim
    
    # Extract key entities
    actors = set(re.findall(r'\b(applicant|resident|caseworker|case manager|intake worker|system admin|administrator|department|manager)\b', normalized))
    tools = set(re.findall(r'\b(form|portal|record|flag|dashboard|report|application|system|workflow|process)\b', normalized))
    stages = set(re.findall(r'\b(intake|triage|review|submission|screening|routing|processing)\b', normalized))
    
    return {
        'claim_count': claim_count,
        'actors': actors,
        'tools': tools,
        'stages': stages,
        'text_len': len(normalized),
        'normalized': normalized,
    }


def compute_multi_factor_similarity(source_struct: dict, target_struct: dict) -> float:
    """
    Compute similarity between two responses using multiple factors:
    1. Claim count similarity
    2. Actor overlap
    3. Tool/artifact overlap
    4. Workflow stage overlap
    5. String-level similarity on normalized text
    """
    # Factor 1: Claim count similarity (0-1 range)
    src_claims = source_struct['claim_count']
    tgt_claims = target_struct['claim_count']
    claim_sim = 1.0 - min(1.0, abs(src_claims - tgt_claims) / max(src_claims, tgt_claims))
    
    # Factor 2: Actor overlap (Jaccard similarity)
    src_actors = source_struct['actors']
    tgt_actors = target_struct['actors']
    if src_actors or tgt_actors:
        actor_overlap = len(src_actors & tgt_actors) / len(src_actors | tgt_actors)
    else:
        actor_overlap = 1.0  # Both empty = match
    
    # Factor 3: Tool/artifact overlap (Jaccard similarity)
    src_tools = source_struct['tools']
    tgt_tools = target_struct['tools']
    if src_tools or tgt_tools:
        tool_overlap = len(src_tools & tgt_tools) / len(src_tools | tgt_tools)
    else:
        tool_overlap = 0.5  # If neither has tools, neutral
    
    # Factor 4: Workflow stage overlap (Jaccard similarity)
    src_stages = source_struct['stages']
    tgt_stages = target_struct['stages']
    if src_stages or tgt_stages:
        stage_overlap = len(src_stages & tgt_stages) / len(src_stages | tgt_stages)
    else:
        stage_overlap = 0.5  # If neither has stages, neutral
    
    # Factor 5: String-level similarity (character-level SequenceMatcher)
    src_text = source_struct['normalized']
    tgt_text = target_struct['normalized']
    string_sim = SequenceMatcher(None, src_text, tgt_text).ratio()
    
    # Weighted combination:
    # - String similarity is most important (50%)
    # - Actor and tool overlap are secondary (20% each)
    # - Claim count and stage overlap are tertiary (5% each)
    combined_sim = (
        0.50 * string_sim +
        0.20 * actor_overlap +
        0.20 * tool_overlap +
        0.05 * claim_sim +
        0.05 * stage_overlap
    )
    
    return combined_sim


def stable_matching(
    source_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    fieldnames: list[str],
    threshold: float = 0.30,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """
    Compute stable best matches between source and target rows using a greedy
    algorithm that respects bidirectional preferences to avoid mismatches.
    
    Returns:
        (matches, unmatched_source_indices, unmatched_target_indices)
        where matches is list of (source_idx, target_idx, similarity)
    """
    # Extract structures for all rows
    source_structs = [extract_claim_structure(row.get('response_text', '')) for row in source_rows]
    target_structs = [extract_claim_structure(row.get('response_text', '')) for row in target_rows]
    
    # Compute all pairwise similarities
    similarities = []
    for i, src_struct in enumerate(source_structs):
        for j, tgt_struct in enumerate(target_structs):
            sim = compute_multi_factor_similarity(src_struct, tgt_struct)
            similarities.append((i, j, sim))
    
    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[2], reverse=True)
    
    # Greedy matching: match highest-similarity pairs first
    # Skip if either row is already matched or similarity is below threshold
    matched_sources = set()
    matched_targets = set()
    matches = []
    
    for src_idx, tgt_idx, sim in similarities:
        if src_idx in matched_sources or tgt_idx in matched_targets:
            continue
        if sim < threshold:
            break  # All remaining will be below threshold (sorted desc)
        
        matched_sources.add(src_idx)
        matched_targets.add(tgt_idx)
        matches.append((src_idx, tgt_idx, sim))
    
    unmatched_sources = [i for i in range(len(source_rows)) if i not in matched_sources]
    unmatched_targets = [j for j in range(len(target_rows)) if j not in matched_targets]
    
    return matches, unmatched_sources, unmatched_targets


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No CSV header found in {path}")
        rows = [dict(row) for row in reader]
        return list(reader.fieldnames), rows


def canonical_key(row: dict[str, str], fieldnames: list[str]) -> tuple[str, ...]:
    key_parts: list[str] = []
    for field in fieldnames:
        value = row.get(field, "") or ""
        if field == "submission_id":
            key_parts.append("<ignored>")
        elif field == "response_text":
            key_parts.append(normalize_response_text(value))
        else:
            key_parts.append(value.strip())
    return tuple(key_parts)


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def generate_report(
    exact_match_pairs: list[tuple[str, str, dict, dict]],
    best_similarity_pairs: list[tuple[str, str, float, dict, dict, dict]],
    unmapped_file2_row: dict[str, str] | None,
    unmatched_source: int,
    unmatched_massaged: int,
) -> str:
    def clean_text(text: str, max_len: int = 80) -> str:
        """Remove newlines and clean text for table display."""
        cleaned = re.sub(r'\s+', ' ', (text or '')).strip()
        return cleaned[:max_len].replace('|', '-')
    
    lines = [
        "# AP1B Reconciliation Report\n",
        "## File References\n",
        "- **file1 (source)**: AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised.csv\n",
        "- **file2 (massaged-prev)**: AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged-prev.csv\n",
        "- **output**: AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged.csv\n",
        "\n## Summary\n",
        f"- Exact normalized matches: {len(exact_match_pairs)}\n",
        f"- Best-similarity pairs (non-exact): {len(best_similarity_pairs)}\n",
        f"- Unmatched file1 rows: {unmatched_source}\n",
        f"- Unmatched file2 rows: {unmatched_massaged}\n",
        f"\n## Table 1: Exact Normalized Matches ({len(exact_match_pairs)} rows)\n",
        "\nfile1_submission_id | file2_submission_id | output_submission_id | response_text\n",
        "---|---|---|---\n",
    ]
    for file1_sid, file2_sid, f1_row, f2_row in exact_match_pairs:
        resp_snippet = clean_text(f1_row.get("response_text", ""))
        output_sid = (f1_row.get("submission_id", "") or "").strip()
        lines.append(f"{file1_sid} | {file2_sid} | {output_sid} | {resp_snippet}\n")
    
    lines.append(f"\n## Table 2: Best-Similarity Matches ({len(best_similarity_pairs)} rows)\n")
    for idx, (file2_sid, file1_sid, sim, f2_row, f1_row, out_row) in enumerate(best_similarity_pairs, 1):
        output_sid = (out_row.get("submission_id", "") or "").strip()
        lines.append(f"\n### Match {idx}\n")
        lines.append(f"- **file2_submission_id**: {file2_sid}\n")
        lines.append(f"- **file1_submission_id**: {file1_sid}\n")
        lines.append(f"- **output_submission_id**: {output_sid}\n")
        lines.append(f"- **similarity**: {sim:.3f}\n")
        lines.append(f"\n**file2_response_text**:\n```\n{f2_row.get('response_text', '')}\n```\n")
        lines.append(f"\n**file1_response_text**:\n```\n{f1_row.get('response_text', '')}\n```\n")
        lines.append(f"\n**output_response_text** (written to output):\n```\n{out_row.get('response_text', '')}\n```\n")
    
    if unmapped_file2_row:
        lines.append("\n## Unmapped file2 Row\n")
        lines.append(f"This file2 row has no matching file1 counterpart:\n")
        lines.append(f"\n- **file2_submission_id**: {(unmapped_file2_row.get('submission_id', '') or '').strip()}\n")
        lines.append(f"- **component_id**: {(unmapped_file2_row.get('component_id', '') or '').strip()}\n")
        lines.append(f"- **response_presence**: {(unmapped_file2_row.get('response_presence', '') or '').strip()}\n")
        lines.append(f"- **response_text**: \n```\n{unmapped_file2_row.get('response_text', '')}\n```\n")
    
    return "".join(lines)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_fields, source_rows = read_rows(NOT_YET_COMPONENTISED)
    massaged_fields, massaged_rows = read_rows(MASSAGED_PREV)

    if source_fields != massaged_fields:
        raise ValueError("Input CSV schemas do not match")

    massaged_counts_by_key: dict[tuple[str, ...], int] = defaultdict(int)
    for row in massaged_rows:
        massaged_counts_by_key[canonical_key(row, massaged_fields)] += 1

    matching_source_rows: list[dict[str, str]] = []
    unmatched_source_rows: list[dict[str, str]] = []
    for row in source_rows:
        key = canonical_key(row, source_fields)
        remaining = massaged_counts_by_key.get(key, 0)
        if remaining <= 0:
            unmatched_source_rows.append(row)
            continue
        massaged_counts_by_key[key] = remaining - 1
        matching_source_rows.append(row)

    unmatched_massaged_rows: list[dict[str, str]] = []
    for row in massaged_rows:
        key = canonical_key(row, massaged_fields)
        remaining = massaged_counts_by_key.get(key, 0)
        if remaining > 0:
            unmatched_massaged_rows.append(row)
            massaged_counts_by_key[key] = remaining - 1

    file2_by_key: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in massaged_rows:
        file2_by_key[canonical_key(row, massaged_fields)].append(row)

    exact_match_pairs: list[tuple[str, str, dict, dict]] = []
    for source_row in matching_source_rows:
        key = canonical_key(source_row, source_fields)
        if file2_by_key[key]:
            file2_row = file2_by_key[key].pop(0)
            file1_sid = (source_row.get("submission_id", "") or "").strip()
            file2_sid = (file2_row.get("submission_id", "") or "").strip()
            exact_match_pairs.append((file1_sid, file2_sid, source_row, file2_row))

    best_pairs: list[dict[str, str]] = []
    pair_mapping: list[tuple[str, str, float, dict, dict, dict]] = []
    
    if unmatched_source_rows and unmatched_massaged_rows:
        # Use improved stable matching algorithm
        matches, _, _ = stable_matching(
            unmatched_source_rows,
            unmatched_massaged_rows,
            source_fields,
            threshold=0.30  # Lower threshold to catch reasonable matches
        )
        
        used_massaged_indices = {tgt_idx for _, tgt_idx, _ in matches}
        
        for src_idx, tgt_idx, sim in matches:
            source_row = unmatched_source_rows[src_idx]
            massaged_row = unmatched_massaged_rows[tgt_idx]
            output_row = dict(massaged_row)
            file1_sid = (source_row.get("submission_id", "") or "").strip()
            file2_sid = (massaged_row.get("submission_id", "") or "").strip()
            output_row["submission_id"] = file1_sid
            best_pairs.append(output_row)
            pair_mapping.append((
                file2_sid,
                file1_sid,
                sim,
                massaged_row,
                source_row,
                output_row
            ))
        
        # Find unmapped file2 row (first one not matched)
        unmapped_file2_row = None
        for idx, massaged_row in enumerate(unmatched_massaged_rows):
            if idx not in used_massaged_indices:
                unmapped_file2_row = massaged_row
                break
    else:
        unmapped_file2_row = None if not unmatched_massaged_rows else unmatched_massaged_rows[0]

    all_output_rows = matching_source_rows + best_pairs
    write_rows(MASSAGED_OUTPUT, source_fields, all_output_rows)

    md_content = generate_report(exact_match_pairs, pair_mapping, unmapped_file2_row, len(unmatched_source_rows), len(unmatched_massaged_rows))
    write_report(MASSAGED_REPORT, md_content)

    print(f"Source rows read: {len(source_rows)}")
    print(f"Massaged-prev rows read: {len(massaged_rows)}")
    print(f"Exact matches written: {len(matching_source_rows)}")
    print(f"Unmatched source rows: {len(unmatched_source_rows)}")
    print(f"Unmatched massaged rows: {len(unmatched_massaged_rows)}")
    print(f"Best-similarity pairs added: {len(best_pairs)}")
    print(f"Total rows written: {len(all_output_rows)}")
    print(f"Output written to: {MASSAGED_OUTPUT}")
    print(f"Report written to: {MASSAGED_REPORT}")


if __name__ == "__main__":
    main()
