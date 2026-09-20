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
