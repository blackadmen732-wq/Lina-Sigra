# Lina Sigra: the full plan, top to bottom

Goal: turn the preview into a complete, trustworthy language with three parts that share one dictionary:

| Part | Job | Who runs it |
| --- | --- | --- |
| **Sigra Code** | General programs: learning, scripts, voice coding | People |
| **Sigra Rules** | Bot decisions: locked box, receipts, replay | Bots and AI agents |
| **Sigra Wire** | Exact messages between agents | Machines |

Each phase ends with something that works and is tested. Nothing moves on with failing tests.

## Where it stands (Nov 25, 2026)

- 30 tests pass. Coverage figures below are from Nov 21 and were not re-measured: parser 87%, interpreter 80%, wire 76%, packets 95%.
- Nov 25 local attack pass: wire messages capped at 64,000 characters, NUL stripped before encoding, a crash on a trailing NEW marker fixed, `risa` refuses non-text host values. Each has a regression test.
- Nov 25 speed pass: the same programs, the same output and the same step counts. Roughly 1.4–1.75x faster on loops, recursion and lists.
- Stress test: 6,000 random broken programs and 4,000 random broken messages, with zero raw crashes.
- Escape attempts (Python, files, internals) are all refused.
- Licence AGPL-3.0, copyright Jahf Mark Aldonza; trademark notice in the README.

## Every known problem

| # | Problem | Part | Phase |
| ---: | --- | --- | ---: |
| 1 | Can't join text and a number (`"risk " + 5` is an error) | Code | 1, fixed |
| 2 | No length of a list or text | Code | 1, fixed |
| 3 | Lists can't be joined (`[1] + [2]`) | Code | 1, fixed |
| 4 | Limits are fixed (10,000 steps), too small for real programs, and the host can't set them | Code | 1, fixed |
| 5 | A user function can take a name the language needs later | Code | 1, fixed |
| 6 | No version number or `--version` | All | 1, fixed |
| 7 | The stress test isn't part of the test suite | All | 1, fixed |
| 8 | No `stop` / `next` inside loops | Code | 2 |
| 9 | Lists hold only simple values; no records (name → value) | Code | 2 |
| 10 | No declared input types: a price sent as text reaches a rule expecting a number | Code + Rules | 2 |
| 11 | No modules: a big project can't be split into files | Code | 2 |
| 12 | `es` and `o` mean different things in Code and Rules | Code + Rules | 2 |
| 13 | Error messages are English only | Code | 2 |
| 14 | `risa` (read) only gives text, so numbers from input need converting | Code | 2 |
| 15 | No error handling (`try`) | Code | 2 |
| 16 | The interpreter has never had an outside security review (a local attack pass was done Nov 25, but that is not an outside review) | Code | 3 |
| 17 | The Rules engine lives in EdgeBot, while Code and Wire live here, with two copies of the codec | Rules + Wire | 3 |
| 18 | Receipts aren't chained or signed | Rules | 3 |
| 19 | Replay isn't run daily, and there's no approval step before a rule goes live | Rules | 3 |
| 20 | Rules can't use time windows ("in the last 30 days"), amounts or lists | Rules | 3 |
| 21 | Wire checks damage, not who sent a message, whether it's old, or whether it's a repeat | Wire | 4 |
| 22 | Wire is text, so it isn't actually small | Wire | 4 |
| 23 | `pesa` builds a packet but can't send or receive one | Wire | 4 |
| 24 | No shared table and no router choosing 1–2 desks | Wire | 4 |
| 25 | The decoder lower-cases words and drops punctuation | Wire | 4 |
| 26 | Can't be installed with `pip`, and there's no `sigra` command | All | 5 |
| 27 | No written specification of the grammar | All | 5 |
| 28 | No tutorial and no website | All | 5 |
| 29 | No editor colours (VS Code) | All | 5 |
| 30 | No automatic tests on GitHub (GitHub Actions billing is blocked) | All | 5 |
| 31 | No contributor agreement and no security policy | All | 5 |
| 32 | Dictionary is 353 words, with no process for adding words | All | 5 |
| 33 | Voice mode not built | Code | later |
| 34 | Trademark only claimed, not registered | Owner | owner |

## Phase 0: owner actions (blockers)

- Fix GitHub Actions billing, so EdgeBot tests and deploys again.
- Merge EdgeBot PR #35 (Decision Replay onto `main`).
- Decide whether to register the trademark (USPTO, about $350 per class).

## Phase 1, v0.2 "usable": fix what a first program runs into (DONE Nov 21, 2026)

- `letra(x)`: a number (or true/false/nothing) as text, so `"risk " + letra(91)` works. The `+` stays strict: text joins only with text.
- `lorga(x)`: the length of a list or a text.
- `[1, 2] + [3]` joins lists, under the same size limits.
- Built-in names can't be redefined by `fora`.
- `run()` takes `steps`, `output` and `depth` limits from the host. The defaults stay safe.
- `VERSION` and `python3 sigra.py --version`.
- The stress test becomes part of the suite (fixed seed, so it's repeatable).
- **Done when:** all tests pass, the examples print totals on one line, and coverage is at least 85% everywhere.
- **Result:** 26 tests pass. Coverage: wire 98%, parser 95%, packets 95%, interpreter 91% (94% overall). The stress
  tests (3,000 broken programs and 3,000 broken messages) are in the suite, and the desk example prints
  "days paused: 1 of 5".

## Phase 2, v0.3 "real programs": types, records, modules

- `stop` / `next` in loops, using real dictionary words (proposed, then owner-approved).
- Records: `desk es {risk: 91, name: "fox"}`, with `desk.risk`.
- Declared types on function inputs and outputs: `fora decide toma risk: numbra -> letra`. Mismatches are caught before running, pointing at the line.
- Modules: `uza "risk.sg"` loads another file's functions. No file access beyond the program's own folder.
- One shared word table for Code and Rules. In Code `es` stays "store"; in Rules the comparison uses `=` the same way, and the old Rules form is still accepted, with a warning.
- Errors in both languages: `linea 4: falta valor despues de sava` / `line 4: missing a value after sava`.
- `try`-style error handling, with a dictionary word.
- **Done when:** a multi-file example with types runs, every type mismatch in the test set is caught before running, and coverage is at least 90%.

## Phase 3, v0.4 "safe for agents": one Rules engine, signed receipts

- Move the Rules engine into this repo as `sigra.rules`. EdgeBot installs it instead of keeping copies.
- An outside security review of the interpreter and Rules engine (a person, plus a deeper fuzzing run). The sandbox claim changes only after the review.
- Receipts: each one carries the hash of the previous one and a host signature. The key lives in host secrets, never in code.
- Replay before promotion: a rule change can't go live without a replay report and an approval record (who proposed it, who approved it, when).
- Rules facts: amounts with units, dates, "in the last N days", simple totals.
- **Done when:** EdgeBot's nightly desk runs on `sigra.rules`, a tampered receipt fails verification, and a rule change without an approval is refused.

## Phase 4, v0.5 "agents talk": authenticated wire, shared table, router

- Packets carry the sender, a time, a one-time number and a signature. Old, repeated or unsigned packets are refused.
- A binary form, measured against plain text and JSON, with honest numbers in the README.
- Case and punctuation preserved for unknown words.
- `pesa` gets a pluggable transport (HTTP first). The host decides who may send what.
- Shared table: desks post Lina sentences; the table combines them, weighted by proven value, and counts copies once.
- Router: picks the 1–2 desks with the best record for the situation. Its own screening cost is measured, not assumed.
- **Done when:** two processes exchange signed packets, a replayed or forged packet is refused, and the router's choice is logged as a Lina sentence.

## Phase 5, v1.0 "a real language": spec, install, docs

- A written spec of the grammar, the meaning of every keyword, and the wire format.
- `pip install lina-sigra`, a `sigra` command, and version compatibility rules.
- Tutorial and a small website, with the Black Fox desk as the worked example.
- A VS Code extension with keyword colours and errors shown inline.
- Tests run on every push (once Actions billing is fixed). Coverage at least 95%.
- `CONTRIBUTING.md` with a contributor agreement (needed for selling separate licences), and `SECURITY.md`.
- A dictionary process: new words are proposed, reviewed, approved by the owner, then frozen forever.
- **Done when:** a stranger can install it, follow the tutorial, and build the desk example without help.

## Later

- Voice mode: speak a program, see what was heard, confirm, run.
- More dictionary words (banking, time), each through the dictionary process.

## Honest limits

- The interpreter is written in Python and walks its own tree, so it's slow next to real languages (the Nov 25 pass made it about 1.4–1.75x faster, not more). That's fine for rules and small programs, not for heavy number crunching.
- Being correct and safe doesn't make people use it. Adoption depends on the Black Fox proof and the demo.
