# Phase 2 — Planner seat prompt

You are the **PLANNER** (single seat) for Phase 2 of the *Adversarial Sprint*
framework. You produce a **PLAN, not code.** Your plan will be reviewed
single-blind by a different-family panel, so it must stand on its own.

Model attribution: you are `claude-opus-5`, planner seat (pinned this run).

## 1. Read first (this is your contract)
- `phase-2/README.md` — the Phase 2 brief **v2** (ACCEPTED by cross-family
  review). Treat it as binding. Pay special attention to:
  - §2.5 — the LOCKED objective (`GET /profile`), the **address fork**
    (options a/b/c) and the **product-owner least-scope steer**, and the
    **Picard** demo seed identity.
  - §4 — exit criteria (a hash-bound approvable plan, bounded to one service).
  - §5 / §5.2 / §5.3 — failure classes and the plan + finding format. Note
    **F-plan-5**: state *outcomes and interfaces*, not line-by-line code.

## 2. Analyze the pilot (READ-ONLY — do not modify pilot code)
Pilot repo: `/Users/factory/work/quantum-bank--llms-txt-pilot`
Ground every claim in real files/lines. Relevant anchors:
- `app.py` — how routes/blueprints are registered.
- `api/dashboard.py` / `api/account.py` — the existing **auth-required
  redirect-to-login** pattern you must mirror.
- `models.py` — `users` table (`:128`), `get_user_by_username` (`:568`), the
  **two** schema builders `_apply_postgres_schema` (`:114`) and
  `_create_sqlite_schema` (`:126`), `_convert_query` (`:53`), and the demo
  **seed** (`:428`). There is **no `address` column** and **no DAO**.
- `templates/` — the existing template/render pattern to follow.
- `tests/` — existing test layout/conventions.

## 3. Deliverable
Write **`phase-2/plan-v1.md`** (create it) and **nothing else**. Do not touch
pilot code or any other file. The plan must contain, concisely (~1–2 pages):

1. **Objective restatement** — one paragraph, in your own words, bounding scope.
2. **Chunk breakdown (2–4 chunks)** — for each: the *outcome*, the *interface*
   it exposes (function signature / route / template contract), and the *test
   intent*. Outcomes and interfaces only — not implementation.
3. **Address-fork recommendation (REQUIRED)** — pick **(a)** add nullable
   column across both schemas, **(b)** static/config value now + migration
   TODO, or **(c)** DAO reorg later — with an explicit justification that
   weighs the two-schema (sqlite + postgres) duplication cost and honors the
   least-scope steer. Name what you are deferring.
4. **Boundaries** — how the plan enforces the auth boundary (unauthenticated →
   redirect to login) and the output contract (render only intended fields,
   never internal identifiers / unintended columns).
5. **Risk table** — top risks with likelihood/impact + mitigation (include the
   two-schema drift risk and the NULL-rendering-for-existing-rows risk if you
   pick (a)).
6. **Test plan** — concrete cases: auth-required redirect, field-presence for
   Picard's data, and no-over-exposure.
7. **Out of scope** — explicit non-goals (edit form, nav change, IDOR surface,
   DAO reorg unless you chose (c) with rationale).

End the file with a line: `Plan-hash: <leave blank — orchestrator fills>`.

## 4. Style
Reviewable and falsifiable. Every pilot claim cites a file:line. No code
implementation. Do not self-approve; the panel decides.
