# Glossary

Terms used throughout this wiki and the repo. Definitions are short; the linked pages have the full context.

| Term | Meaning |
|---|---|
| **Adversarial sprint** | A multi-model coding loop where different model families handle different roles (planner, reviewer, executor, validator) and structural separation between them produces independent review. |
| **Chunk** | A bounded unit of work within a sprint. One chunk = one test-first cycle: design test, lock, verify RED, implement, verify GREEN, validate. |
| **Chunk-close token** | An HMAC-SHA256-signed JSON file (`chunk-N.token.json`) that attests a chunk was reviewed by two cross-family reviewers who both returned ACCEPT-class verdicts. The next chunk cannot start without one. |
| **Cross-family** | Two models from different model families (e.g., Anthropic/Claude vs xAI/Grok). Two passes from one family are one opinion twice. |
| **EvidenceBundle** | A compact, signed JSON artifact produced by `local_backend.py` containing test results, locked-hash verification, and optional security scan. Validators read the bundle instead of re-running pytest. |
| **Family** | Model lineage, not a marketing label. Anthropic/Claude, OpenAI/GPT, Google/Gemini, xAI/Grok, etc. Provenance is curated by hand in `MODEL_FAMILY_MAP`, not inferred. Unknown provenance cannot satisfy a separation constraint. |
| **Family guard** | A pure-function check in `sprint_loop/state.py` that verifies family separation before any droid exec fires. Refuses on collision or unknown provenance. |
| **GREEN** | A locked test passes. Must be the same hash that was observed failing RED. |
| **GROK** | The planning stage: the planner drafts problem analysis, acceptance criteria, risks, and test strategy. |
| **HMAC-SHA256** | The signing algorithm used for EvidenceBundles and chunk-close tokens. Key comes from `EVIDENCE_SIGNING_KEY`. |
| **Locked test** | A test file whose content hash is recorded in a lock manifest. The executor cannot modify it. A hook blocks writes; the hash is re-checked at GREEN. |
| **Model family map** | A curated dictionary in `tools/sprint_loop/config.py` mapping model IDs to (provider, family) tuples. The source of truth for family separation. |
| **Orchestrator** | The `sprint-loop.py` entry point that coordinates all five roles and manages pause/resume gates. |
| **Plan-lint** | A deterministic pre-review tier (`tools/plan-lint.py`) that catches machine-checkable contract defects in build plans before a frontier panel round is spent. BLOCK-only; a PASS is never approval. |
| **RED** | A locked test fails for the expected behavioral reason. Syntax errors, import failures, and missing fixtures are invalid RED. |
| **Reconcile** | The human gate after plan review. The operator walks the critique list and rules accept/reject/amend on each finding. |
| **Role** | One of five seats: planner, plan reviewer, test designer, executor, validator. Each has different tool permissions and family constraints. |
| **Silent green** | The platform's default failure mode: an agent reports success for work it did not do, and the report looks exactly like a report of work it did. The core finding this project exists to address. |
| **Sprint** | One end-to-end run of the adversarial loop: plan, review, reconcile, chunk, execute, validate, report. |
| **Validator panel** | A group of at least two validators from distinct model families who review the same chunk. Any REJECT blocks. |
| **Vendor adapter** | A module in `tools/adapters/` that translates a vendor's raw envelope into a neutral shape. `factory.py` is the only one today; Codex, Claude Code, and Ollama are future adapters. |
