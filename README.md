# MantiQ / Solidity

**ESL Engineering Software Lab: one milestone escrow, several kinds of evidence.**

An English, 10-15 minute educational demonstration for mixed technical/business
audiences. Amp prepared an intentionally defective fixture and its correction.
This is not an audit, production escrow, or a claim that AI happened to produce this defect.

- Presentation: https://zuwasi.github.io/Public-html-pages/mantiq-solidity/
- Automated evidence tour: https://zuwasi.github.io/Public-html-pages/mantiq-solidity/dashboard.html?autoplay=1
- Source: https://github.com/zuwasi/MantiQ-Solidity

## Start locally

Python 3.10+ and Node.js 22+. The Python server has **no third-party dependencies**.
Tested with Python 3.14 and Node 22.21 on Windows.

```powershell
Set-Location C:\Amp_demos\MantiQ-Solidity
npm ci --ignore-scripts
python demo.py serve
```

Open http://127.0.0.1:8765/dashboard.html and select **Run local checks**.
The EVM runs in-process: no wallet, listening blockchain RPC, public chain, or real funds.
The server listens only on loopback and rejects cross-origin run requests.

```powershell
python demo.py run       # full local workflow
python demo.py export    # publishable summary from the latest completed run
npm test                # contract tests alone
python -m unittest discover -s tests -v
```

Exit codes: **0** all stages passed; **1** failed execution/check; **2** blocked
integration or findings needing review. Code 2 is intentionally not a green release gate.
`runs/<run-id>/` retains raw logs and tool artifacts locally. `web/evidence/replay.json`
contains a reviewed summary for public playback, not raw third-party reports.
Export checks that the evidence source hashes still match the current source.

## What the audience sees

The buyer funds a single supplier milestone. Before the deadline the buyer can
release payment; at or after it the buyer can refund. Settlement is terminal.

The buyer signs a transaction to an **untrusted intermediary**, which calls `release()`.
The defective fixture checks `tx.origin == buyer` and releases funds. The corrected
fixture checks `msg.sender == buyer` and rejects that same intermediary call.
The money goes to the configured supplier, not an arbitrary attacker. The scenario
depends on the buyer signing the intermediary interaction. Never deploy these fixtures
with real funds. The fixed version is also educational and has not been independently audited.

## Evidence lanes

| Lane | What runs | What it does not establish |
| --- | --- | --- |
| Local EVM | solc 0.8.37, optimized Shanghai bytecode, Ganache; regression tests and fast-check generated transaction sequences | Production safety or all possible EVM behaviors |
| Wolfram | Independent finite enumeration, deadline boundaries, counterexample search | An unbounded proof or bytecode equivalence |
| Lean 4 | Six theorems over an abstract transition system, pinned 4.33.1 | EVM calls/gas/reentrancy or implementation correspondence |
| Olympix | Optional authenticated CLI Solidity scan | A clean scan is not proof; access is separate from the VS Code extension |
| SBOMator | Local installed tooling inventory, cached OSV advisory matching, report output | Solidity semantic correctness, exhaustive compiler advisories, or fresh threat intelligence |

The core regression suite checks authorization, deadline-1/deadline/deadline+1,
single settlement, recipient-failure rollback, invalid construction, exact balances
(refunds account for gas), and generated action sequences. Fast-check uses seed
20260920, 20 sequences, varying amounts/roles/monotone times, shrinking on failure,
and an eventual authorized settlement to prevent a rejection-only test corpus.

See [formalization scope](docs/formalization.md) for theorem names and assumptions.
These are **model proofs**, not formal verification of Solidity source or bytecode.

## Optional tools and licensing

### Wolfram and Lean

Provide a licensed `wolframscript` on PATH. Tested with Wolfram 15.0.1.
Install Lean using elan; `lean/lean-toolchain` pins the version, with no Mathlib dependency.

```powershell
wolframscript -file wolfram/check.wls wolfram/result.json
lake -d lean build
```

### Olympix

Initial environment inspection confirmed VS Code extension `olympixai.olympix@2.0.2`.
It did **not** establish CLI authentication. The initial demo labels Olympix blocked.
We never read VS Code secret storage or copy credentials into the project.

1. Install the official CLI using https://olympix.github.io/installation/ and verify its published hash.
2. Authenticate yourself with `olympix login -e YOUR_EMAIL` and the emailed code.
3. Confirm trial/free-plan CLI and JSON report entitlement with Olympix.
4. Explicitly opt into scanning the synthetic contract sources:

```powershell
python demo.py run --olympix
# Or enable the same opt-in for dashboard-triggered runs:
python demo.py serve --olympix
```

This may transmit synthetic Solidity source to Olympix. Never use private source,
secrets or real wallet material without checking your account's data-handling terms.
Raw findings remain local pending triage; the public summary does not manufacture a
detection or claim that the CLI integration has been tested without account access.

### SBOMator

Use a separately licensed SBOMator installation. Default on this workstation:
`C:\Sbomator_1.4.x`. Override via `SBOMATOR_HOME` and optionally `SBOMATOR_PYTHON`.
The runner invokes the existing CLI with `--skip-db-update --include-dev
--no-lockfile --cve-mode local_osv --no-grype`. Grype is deliberately disabled because
its wrapper refreshes its database; the demo is intended to use cached local data.
Missing dependencies, unanalyzed components, and unresolved inventory fields remain
visible. An exit-0 scan is not automatically a clean result.

Ganache is an older, isolated development dependency and can contribute advisory
findings. No production service uses it here; this distinction is **not** an automatic
vulnerability dismissal. The demo does not suppress or remediate findings just to
produce a green screen. Node 22 may print a Ganache native-uWS fallback warning;
the pure-JavaScript fallback is used and executable checks still run.

## Presentation and replay

`web/index.html` is a self-contained horizontal slide deck. Arrow keys, Space,
touch swipes and mouse drags navigate; typography falls back to system sans-serif
if Google Fonts is unavailable. `docs/presenter-notes.md` gives the 10-15 minute script.

`web/dashboard.html` can run on GitHub Pages without Python. That is **recorded
evidence replay**, not a live scan or EVM. Play/pause/step/reset animate the evidence
tour; reduced-motion users can step manually. On localhost the same UI detects the
Python API and offers live execution. The dashboard never submits public-chain transactions.

For browser QA/recording, install Playwright separately (`python -m pip install
playwright`, `python -m playwright install chromium`) and use `scripts/check_ui.py`.
These tools are not needed to view or run the dashboard itself.

## Repository map

- `contracts/`: fixed escrow, intentionally defective override, test-only actors.
- `scripts/evm.mjs`: compilation, regression/property tests, measured scenario output.
- `lean/`, `wolfram/`: independent models and checks.
- `demo.py`: local orchestration, source hashes, evidence export, loopback server.
- `tests/`: runner/API regression tests.
- `web/`: presentation, dashboard, public evidence summary and visual captures.
- `docs/PLAN.md`: agreed scope, milestones and acceptance checks.

## License

Original demo source and presentation: MIT, see [LICENSE](LICENSE).
Olympix, Wolfram, SBOMator and other third-party tools retain their own licenses
and are **not redistributed or relicensed** by this repository. Node dependencies
retain their package licenses. No endorsement by those vendors is implied.
