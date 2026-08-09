"""sprint_loop — adversarial-sprint command-orchestrated runner package.

This is the Phase 4.5 deliverable per PRD §11. The package exposes:

  - ``state``    : pure data-classes for the run state machine
  - ``config``   : Config dataclass + parse from CLI + JSON
  - ``droid``    : thin wrapper around ``tools/run-with-model.sh`` +
                   ``tools/adapters/factory.py`` (the OPERATING-RULES §14
                   discipline)
  - ``backends`` : validation backend interface (Track B): LocalBackend
                   shells out to ``tools/orchestrate-review.py``;
                   CIBackend is a stub (interface only per the prompt)
  - ``per_chunk``: the per-chunk inner loop, composing the existing
                   ``phase-1/scripts/{lock,valid-red,verify-green}.py``
                   and ``phase-3.2/evidence/local_backend.py``
  - ``prompts``  : pluggable role-prompt templates per role

The CLI entry point is ``tools/sprint-loop.py`` (a sibling module in the
``tools/`` directory, kept thin).

The runner is bounded by OPERATING-RULES §17 — refuse unbounded foundation
programs. One phase, three tracks, no scope creep.
"""
__version__ = "0.1.0"
__phase__ = "phase-4.5"
