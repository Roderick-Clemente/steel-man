# Findings

The live runs found four structural failure modes and one hand-run pilot that showed how the method behaves before the tooling is in place. Each finding is sourced, reproducible, and comes with a committed artifact or a re-runnable probe. This is the record the method is built to prevent.

## The four headline findings

- **[Silent green](silent-green.md)** — the platform's default failure mode is success. Four probes hit the same shape: zero work, zero turns, every tool denied, or a model silently downgraded, all reporting `exit 0`. The report looks exactly like a real pass. The only fix is a guard that reads the transcript and fails closed.

- **[Reference guard](reference-guard.md)** — context isolation is real at the agent channel, but absent at the filesystem. A read-only validator recovered a prior agent's secret from `~/.factory/sessions` using only `Grep`. `droid search` turned out to be a second, supported leak path. The guard that closes both is the same primitive the framework ships as a plugin.

- **[Fake pass](fake-pass.md)** — a forged transcript passed rungs 3, 5, and 6 with no real validation. Three permissive defaults aligned: an unmatched `tool_use` returned `is_error=None`, the gate checked `is True`, and the run-level `is_error` flag was ignored. The fix is one line. The forged input is committed as a fixture.

- **Cross-version validation** — in `planning/phase-3.1/RESULTS.md`, a same-family test-author encoded a test-independence bias. Grok rejected it with correct attribution; Gemini looked at the identical failure and returned `ACCEPT`. The deterministic gate caught it every time. The finding is discussed on the [silent green](silent-green.md) page because it is the same class of failure: a green signal over a red reality.

## The first H1 observation

- **[First H1 evidence](first-h1-evidence.md)** — the pilot run against QuantumBank was the method executed by hand. Four units (`/llms.txt`, `/robots.txt`, `/llms-full.txt`, `/sitemap.xml`) went through an executor, then Grok and Kimi in fresh contexts. The run showed that cross-family review can catch things the executor missed. It also showed that the wrong model ran a five-chunk refactor and nothing surfaced it until the operator read the commit record.

## How to read these

Each page starts with what was observed, names the source file or probe, and ends with what the method does about it. The claims are scoped to the CLI version and commit under which they were measured. If the evidence looks thin, that is stated too. See [the method](../method.md), [security](../security.md), and the [overview](../overview/index.md) for the design the findings protect.
