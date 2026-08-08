# Fun facts

A few surprising moments from the five-day adversarial sprint, recorded here because they are more memorable than the commit log that produced them.

## Phase 3 went from kickoff to merge in hours

Phase 3 was the fastest phase of the entire sprint. The kickoff happened in the morning, and the merge to `main` happened the same day. The work was a focused strike on the review pipeline: a single pass through the orchestration, a tight set of findings, and a fast reconcile. The difference between Phase 3 and the earlier phases was not the difficulty of the work; it was that the team finally had a reusable harness, a shared vocabulary, and a muscle memory for landing evidence-backed changes.

## Grok found the blocking issues that Gemini missed

In one round of multi-model review, Grok spent about 59,000 tokens and surfaced five blocking issues. Gemini, running on the same inputs, spent roughly 716,000 tokens and missed the same five. The gap was not about total effort; it was about where the effort went. Gemini's output was broad and thorough in the wrong places, while Grok zeroed in on the exact diffs and contracts that mattered. The lesson was not that one model is universally better, but that token count is a poor proxy for signal quality and that the framework needs to weight models by their demonstrated hit rate on the current task, not by their enthusiasm.

## The team used the orchestration script to review the orchestration script

At one point the orchestration script was run against its own source code. The circularity was intentional: if the review pipeline could not cleanly review the tool that runs reviews, then the tool was not ready. The script passed, which was either reassuring or slightly suspicious, depending on how you look at it. The team treated it as a calibration run and documented the result rather than celebrating it, because a system that validates itself is also a system that can blind itself.

## The `.venv` exclusion needed a `./` prefix

During a security scan, `bandit` kept flagging files inside `.venv` even though the directory was supposed to be excluded. The fix was embarrassingly small: the exclusion pattern needed the `./` prefix. Writing `.venv` was not enough; writing `./.venv` was. It was a reminder that tooling is often literal in ways that feel unnecessary, and that the difference between "ignored" and "scanned" can be two characters. The correction was committed and the scan went green.

## Grok caught a `None == None` SHA bypass in round three

In the third round of review, Grok found a subtle bypass in the SHA handling logic. The code compared two values that could both be `None`, and when both were `None` the comparison returned `True` even though no actual SHA verification had happened. The function looked like it was checking integrity, but it was really just passing a null check. This was the kind of bug that is easy to overlook in review because the line itself is short and the intent is obvious to a human reader. Grok flagged it as a real issue, not a style nit, and it was fixed before merge. It became the canonical example of why the third review round matters: the first two rounds find the obvious things, and the third round finds the things you have already stopped looking for.
