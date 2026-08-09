"""Role-prompt templates for the loop runner.

Each role has a markdown template that takes a context dict and
substitutes ``{{key}}`` placeholders. The runner renders the template
to a per-invocation ``prompts/<role>-<runid>.md`` file and passes that
to ``droid exec -f <path>``.

Templates intentionally *describe the role + the inputs* — never the
implementation. PRD §13: "Don't give the executor the answer"; the
executor prompt says the problem, the chunk spec, the acceptance
criteria, the locked-test contract, the rollback plan — but not the
``os.environ.get(NAME, ...)`` style fix.

Reused from existing primitives:
  - ``tools/validator-spec/llms-doubled-charset.md`` is the format
    reference for ``validator.md``: same blinded context, same verdict
    line spec.
  - ``tools/render-blind-prompt.py`` strips executor context from
    reviewer prompts (``tools/sprint_loop/prompts/render`` will
    shell out to it for the plan-reviewer role — never raw
    string-replace the runner code).
"""
