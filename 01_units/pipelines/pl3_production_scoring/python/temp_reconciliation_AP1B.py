from __future__ import annotations

from pathlib import Path

NOT_YET_COMPONENTISED = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised.csv"
)
MASSAGED_PREV = Path(
    "/Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/AP1-umbrella/AP1B/01_pipelines/pl1A_canonical_population/02_runs/01_cleaning/AP1B_canonical_population_SectionBResponse_2026_03_18_not_yet_componentised_massaged-prev.csv"
)


def read_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        return handle.readlines()


def main() -> None:
    source_lines = read_lines(NOT_YET_COMPONENTISED)
    massaged_prev_lines = read_lines(MASSAGED_PREV)

    print(f"Read {len(source_lines)} lines from: {NOT_YET_COMPONENTISED}")
    print(f"Read {len(massaged_prev_lines)} lines from: {MASSAGED_PREV}")


if __name__ == "__main__":
    main()
