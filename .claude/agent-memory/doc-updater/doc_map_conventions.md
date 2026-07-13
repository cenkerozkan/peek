---
name: doc-map-conventions
description: How PEEK's roadmap.md/decisions.md/structure.md are structured and cross-referenced; recurring facts that live in multiple docs and must be kept in sync together.
metadata:
  type: project
---

PEEK's doc set (read CLAUDE.md doc-map table first every time — it is short and
authoritative) has these house conventions, confirmed across the Phase 7/8 update
(2026-07-13):

- **roadmap.md** is a pure checklist (`[x]`/`[~]`/`[ ]`, header ⬜/✅) of *order of
  work*, not rationale — rationale belongs in decisions.md and is linked by
  `see decisions.md #N`. When a phase completes, tick every bullet AND update the
  header emoji; do not leave a phase headed ⬜ with all-`[x]` bullets underneath.
  Roadmap bullets sometimes need small amendments in place (e.g. Phase 0's "src.
  prefix" bullet was annotated "Superseded in Phase 7" rather than deleted) so the
  history of what was actually tried stays legible.
- **decisions.md** entries are dated and numbered sequentially; when a decision is
  *corrected* (not reversed), the pattern used is a lettered sub-entry (e.g. `14a.`)
  appended after the original, with the original's header timestamp updated to
  "Accepted (orig-date; amended new-date)". This preserves the original rationale
  intact while recording the correction and its own why. New unrelated decisions
  get the next free top-level number, added just before the "Still open" section
  at the bottom.
- **structure.md**'s file tree uses `✓` / `(planned)` markers per file. This tree
  drifts easily — during this update it was found stale (several Phase 6 files
  still marked `(planned)` even though roadmap.md already had Phase 6 ✅). Worth
  spot-checking this tree against `find src tests -name '*.py'` whenever touching
  structure.md, not just trusting the roadmap's phase checkmarks.
- **backlog.md** entries always pair "Why removed/deferred" with a "Revival
  condition" — never just log a cut without stating what would bring it back.
- Cross-file fact that must stay in sync: the **PyPI distribution name vs. import/
  command name split** (`peek-sql` on PyPI, `peek` for `import peek` / console
  command / `python -m peek`) appears in `pyproject.toml` comments,
  `docs/decisions.md` #14/#14a, `docs/roadmap.md` Phase 8/9, and `README.md`. If
  this ever changes again, grep all four.
- CLAUDE.md itself carries no install/launch commands (`grep -n "uvx" CLAUDE.md`
  is empty by design) — that detail lives only in README.md + decisions.md #14,
  keeping CLAUDE.md lean as its own rule requires.
