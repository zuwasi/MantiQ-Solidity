# MantiQ / Solidity presenter notes

Target: 10-15 minutes. Keep the dashboard honest: recorded evidence is playback, while the local API is execution.

1. **Title (0:30)** Introduce MantiQ and ESL Engineering Software Lab. This is an educational fixture, not an audit.
2. **Purpose (0:45)** The goal is traceable claims, not one oversized “secure” verdict.
3. **Rules and boundary (1:00)** Release is before the deadline; refund is at or after it. Both require the buyer and a funded state.
4. **Defect and transaction path (1:30)** Amp was used to prepare an intentionally seeded fixture and correction. The buyer must sign the intermediary interaction. `tx.origin` preserves the buyer, while `msg.sender` identifies the untrusted intermediary. Funds still go to the fixed supplier.
5. **Local EVM (1:15)** The same intermediary call releases the defective contract and reverts on the fixed contract. Mention deadline and rollback regressions.
6. **Wolfram (0:50)** Explain finite enumeration as an independent model check, not exhaustive EVM verification.
7. **Lean (1:15)** State what is proved, then emphasize that no source/bytecode correspondence theorem exists.
8. **Olympix (0:40)** VS Code extension 2.0.2 is installed. CLI authentication is independent and currently blocked. Never imply blocked means passed.
9. **SBOMator (0:40)** It inventories dependencies and known CVEs. It does not prove Solidity behavior.
10. **Evidence (0:50)** Point out revision, dirty state, source SHA-256 hashes, timestamp, and explicit statuses.
11. **Dashboard (2:30)** Open the tour, step through stages, compare defective/fixed panels, and download JSON. If local API is reachable, run checks and show the mode changing from recorded replay to live local result.
12. **Takeaway (0:45)** Each tool supports a bounded claim. There is no production wallet, public RPC, real money, audit, or blanket security guarantee.

## Demo commands

From the repository root:

```powershell
python demo.py serve
```

Open the URL printed by the server, then choose **Run local checks**. For a checks-only run:

```powershell
python demo.py run
```

If the command names differ in the final `demo.py`, use `python demo.py --help` and update these two commands before presenting. Do not open the HTML via `file://`, because browsers may block the evidence fetch.

## Recovery

- If replay loading fails, keep the visible **Missing evidence** state and explain that no sample success is substituted.
- If local API discovery fails, the run button remains disabled; continue with the clearly labelled recorded replay.
- If a stage is failed, blocked, or has findings, discuss it as-is. Never summarize the dashboard as “all secure.”
