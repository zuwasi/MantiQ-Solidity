# Escrow formalization scope

This directory contains an abstract educational model, not a verification of a Solidity implementation.

## Normalized model

Deployment fixes distinct, nonzero buyer and seller addresses, a positive funded amount, and a deadline strictly after the deployment timestamp. The initial state is `Funded` and the escrow ledger holds the full amount.

The fixed transition accepts release only when `caller == buyer`, `now < deadline`, and the state is `Funded`. It atomically changes the state to `Released`, empties escrow, and credits the seller with the full escrow balance. Refund analogously requires `caller == buyer`, `now >= deadline`, and `Funded`, then atomically changes the state to `Refunded`, empties escrow, and credits the buyer. Every failed call is the identity transition.

The defective transition replaces release authentication with `origin == buyer`. The concrete witness uses buyer `1`, intermediary caller `3`, origin `1`, deadline `5`, and time `4`: defective release succeeds although the fixed transition rejects it.

## Evidence and theorem scope

| Claim | Lean evidence | Wolfram evidence | Status |
|---|---|---|---|
| Unauthorized fixed release is rejected | `unauthorized_release_rejected` | finite caller/time search | Formally proved |
| Calls failing both guards leave the ledger unchanged | `failed_call_unchanged` | finite transition checks | Formally proved |
| Released and Refunded are absorbing | `terminal_absorbing` | finite terminal-state search | Formally proved |
| Release and refund time windows are exclusive | `release_refund_time_exclusive` | checks deadline-1, deadline, deadline+1 | Formally proved |
| Atomic settlement conserves escrow plus credited balances | `conservation` | finite ledger search | Formally proved |
| `tx.origin` permits intermediary release | `defective_origin_counterexample` | concrete witness in JSON | Formally proved for the abstract witness |

`conservation` concerns the model's abstract ledger total. A successful transition moves the entire current escrow field to exactly one recipient in one indivisible model step. It does not establish Ether conservation in EVM execution.

## Deliberate boundaries

The model omits EVM external-call behavior, gas, reentrancy, revert propagation, fallback/receive behavior, forced Ether, self-destruct semantics, timestamp manipulation, transaction ordering, ABI details, and unsigned-integer overflow. Natural numbers model balances and timestamps. Atomic crediting is an assumption encoded directly in the transition, not a proof that a contract's low-level transfer is atomic or successful.

No correspondence theorem links these definitions to Solidity source or bytecode. Therefore these results must not be described as implementation verification, audit evidence, or a proof of deployment safety. They prove only the stated transition-system properties.

## Reproduction

From `lean/`, run `lake build`. From the project root, run:

```text
wolframscript -file wolfram/check.wls wolfram/result.json
```

The Wolfram script independently enumerates small state, caller, origin, and boundary-time spaces, writes version/platform and check evidence as JSON, and exits nonzero on any mismatch.
