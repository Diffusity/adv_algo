# Group 6 contribution record (working draft)

This record supports the CRediT/task-division statement in
`report/main.tex`. It is a working draft: each student should confirm their
wording and evidence before the final submission and viva. The manuscript's
published statement should match this record.

## Division

| Student | ID | Primary contribution | Main evidence |
| --- | --- | --- | --- |
| Astha Patel | 202611065 | Conceptualization, methodology, literature review, Introduction and Related Work, original draft, coordination | `report/main.tex` Sections I--II; project plan and review |
| Hirali Desai | 202611066 | Search engine, incremental oracle, unit tests, validation, trace/demo implementation | `src/mxaid/search.py`, `src/mxaid/oracles.py`, `tests/`, `web/` |
| Shantanu Singh Sandu | 202611044 | Benchmark harness, experiment execution, formal analysis, data curation | `experiments/`, `results/raw/full.csv`, `results/summary/` |
| Jyoti Mauriya | 202611023 | Investigation, density and multi-query visualization, documentation, review/editing | `report/figures/`, `experiments/plots.py`, report revisions |
| Nevil Nandasana | 202512009 | Methodology, validation, data curation, literature and reference checking | `results/summary/validation.json`, reference list, test checks |
| Parth Maharaja | 202512061 | Project administration, experiment/demo integration, report review/editing | `web/`, integration checks, final report review |

## Shared responsibilities

- All members reviewed the problem formulation, results, and final manuscript.
- All members participated in reproducibility checks and the demonstration.
- The group jointly owns the claims in the report; individual roles describe
  primary effort, not exclusive ownership.

## Deliverables

| Deliverable | Location | Owner(s) |
| --- | --- | --- |
| Core package and tests | `src/mxaid/`, `tests/` | Hirali, Shantanu |
| Full benchmark matrix | `results/raw/full.csv` | Shantanu, Nevil |
| Validation and summaries | `results/summary/` | Shantanu, Nevil |
| Density figure and report tables | `report/figures/`, `report/tables/` | Jyoti, Shantanu |
| Static web demo | `web/` | Hirali, Parth |
| IEEE report and PDF | `report/main.tex`, `report/main.pdf` | Astha, all reviewers |
| Documentation and ADRs | `README.md`, `GLOSSARY.md`, `docs/adr/` | Jyoti, Astha |

## Before submission

- [ ] Each student confirms their CRediT wording and task description.
- [ ] The group confirms the order of authors and student IDs in the report.
- [ ] The latest `results/raw/full.csv`, `report/main.pdf`, and
      `web/demo_data.js` are the versions being submitted.
- [ ] The demo is smoke-tested from a fresh local server.
- [ ] `python -m pytest` passes and `results/summary/validation.json` still
      reports zero mismatches.
