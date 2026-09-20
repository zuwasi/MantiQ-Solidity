# MantiQ-Solidity: agreed demo plan

Audience: mixed technical/business. English, ESL/MantiQ branding, 10-15 minutes.
Local project: C:\Amp_demos\MantiQ-Solidity. Public MIT source: zuwasi/MantiQ-Solidity.
Presentation and recorded-evidence dashboard: existing ESL Public-html-pages site.

## Scope

One buyer, one supplier, one funded milestone. Direct buyer release before the
deadline; direct buyer refund at/after the deadline. A terminal escrow cannot settle
again. A deliberately defective release uses tx.origin; the corrected version uses
msg.sender. An untrusted intermediary demonstrates the difference using test Ether.
The buyer must sign the intermediary interaction: this is not a remote unauthenticated
drain. Funds go to the configured supplier, not an arbitrary attacker address.

1. Inspect Olympix installation and local tools. Verify extension version; do not
   extract VS Code credentials. CLI access is independent of extension installation.
2. Implement and execute contract regressions, deadline boundary checks and generated
   transaction sequences against a local in-process EVM. Never use a public RPC.
3. Independently model transitions in Wolfram and Lean. Build proofs with no proof
   placeholders. Explicitly exclude bytecode equivalence and real-world guarantees.
4. Integrate optional Olympix CLI and licensed local SBOMator. Missing access is
   BLOCKED, tool errors are FAILED, findings are evidence, not automatic false positives.
5. Python stdlib server and browser dashboard: live local checks and clearly labelled
   recorded-evidence playback. Preserve source hashes and timestamps on results.
6. Build horizontal HTML slides with keyboard, touch, mouse and progress navigation.
   Verify desktop/mobile views, live API interaction, replay controls, and recording.
7. Review public artifacts for secrets, license restrictions and unsupported claims;
   publish MIT source plus the presentation/replay to the existing public site.

## Non-goals

No Parasoft v1, production deployment, real funds, wallet connection, token pricing,
regulatory certification, guarantee of security, or automatic AI-generated fix during
the live show. Amp created the prepared defective/fixed teaching fixtures; playback
does not pretend to call an AI agent. Third-party tools retain their own licenses.

## Acceptance

The same intermediary call releases the defective escrow but reverts on the fixed
escrow. Unauthorized direct calls fail. Deadline-1 and deadline differ. A second
settlement is rejected. Failed recipient transfers roll back state. Generated action
sequences agree with an independent reference state machine. Real evidence backs
every published green check; unavailable integrations remain visible.

## Checkpoint: 2026-09-20

The MIT repository, presentation, dashboard, and recorded evidence are published.
Verification passed: 12 EVM checks, 20 generated transaction sequences (108 actions),
7,776 Wolfram model cases, six Lean model theorems, five Python tests, and
desktop/mobile browser checks including live local execution and public replay.
SBOMator reported 368 components, eight vulnerability entries, and 77 unresolved
inventory fields. These findings remain open, not a clean release verdict.

Olympix CLI 0.11.119 is installed locally at
`C:\Users\danie\bin\olympix.exe`; its SHA-256 matched the official Windows x64
release checksum. The binary is not redistributed in this repository.
Login was rejected with an account-access message indicating that the email had
not requested access. The user contacted Olympix support; integration is paused
pending their response. No authenticated Olympix scan has completed, and the
published evidence correctly retains BLOCKED status.

Resume after support confirms access:

1. Run `olympix login -e YOUR_EMAIL` and enter the newest emailed code in the local
   terminal. Do not publish codes, tokens, or credential files.
2. Run `python demo.py run --olympix` to capture actual scan results.
3. Review the findings, including whether the deliberately defective fixture is
   detected; do not assume the scan will identify it.
4. Export source-matched evidence, refresh the presentation and recording as needed,
   verify the dashboard, and republish the reviewed artifacts.

Official CLI documentation: https://olympix.github.io/cli/
The documented static-analysis tier is free; premium test generation is outside v1.
