import Std

namespace MantiQEscrow

abbrev Address := Nat

inductive EscrowState where
  | funded
  | released
  | refunded
  deriving DecidableEq, Repr

structure Terms where
  buyer : Address
  seller : Address
  amount : Nat
  deployedAt : Nat
  deadline : Nat
  buyer_ne_seller : buyer ≠ seller
  buyer_nonzero : buyer ≠ 0
  seller_nonzero : seller ≠ 0
  amount_positive : 0 < amount
  deadline_after_deployment : deployedAt < deadline

structure Ledger where
  state : EscrowState
  escrow : Nat
  sellerReceived : Nat
  buyerReceived : Nat
  deriving DecidableEq, Repr

inductive Operation where
  | release
  | refund
  deriving DecidableEq, Repr

structure Call where
  operation : Operation
  caller : Address
  origin : Address
  now : Nat
  deriving DecidableEq, Repr

def initialLedger (t : Terms) : Ledger :=
  { state := .funded, escrow := t.amount,
    sellerReceived := 0, buyerReceived := 0 }

def releaseEnabled (t : Terms) (l : Ledger) (c : Call) : Prop :=
  c.operation = .release ∧ c.caller = t.buyer ∧ c.now < t.deadline ∧
    l.state = .funded

def refundEnabled (t : Terms) (l : Ledger) (c : Call) : Prop :=
  c.operation = .refund ∧ c.caller = t.buyer ∧ t.deadline ≤ c.now ∧
    l.state = .funded

def fixedTransition (t : Terms) (l : Ledger) (c : Call) : Ledger :=
  match c.operation with
  | .release =>
      if c.caller = t.buyer ∧ c.now < t.deadline ∧ l.state = .funded then
        { state := .released, escrow := 0,
          sellerReceived := l.sellerReceived + l.escrow,
          buyerReceived := l.buyerReceived }
      else l
  | .refund =>
      if c.caller = t.buyer ∧ t.deadline ≤ c.now ∧ l.state = .funded then
        { state := .refunded, escrow := 0,
          sellerReceived := l.sellerReceived,
          buyerReceived := l.buyerReceived + l.escrow }
      else l

def defectiveTransition (t : Terms) (l : Ledger) (c : Call) : Ledger :=
  match c.operation with
  | .release =>
      if c.origin = t.buyer ∧ c.now < t.deadline ∧ l.state = .funded then
        { state := .released, escrow := 0,
          sellerReceived := l.sellerReceived + l.escrow,
          buyerReceived := l.buyerReceived }
      else l
  | .refund => fixedTransition t l c

def total (l : Ledger) : Nat :=
  l.escrow + l.sellerReceived + l.buyerReceived

theorem unauthorized_release_rejected (t : Terms) (l : Ledger) (c : Call)
    (hop : c.operation = .release) (hcaller : c.caller ≠ t.buyer) :
    fixedTransition t l c = l := by
  simp [fixedTransition, hop, hcaller]

theorem failed_call_unchanged (t : Terms) (l : Ledger) (c : Call)
    (h : ¬ releaseEnabled t l c ∧ ¬ refundEnabled t l c) :
    fixedTransition t l c = l := by
  cases hop : c.operation <;>
    simp_all [fixedTransition, releaseEnabled, refundEnabled]

theorem terminal_absorbing (t : Terms) (l : Ledger) (c : Call)
    (hterminal : l.state = .released ∨ l.state = .refunded) :
    fixedTransition t l c = l := by
  rcases hterminal with hstate | hstate <;>
    cases hop : c.operation <;> simp [fixedTransition, hop, hstate]

theorem release_refund_time_exclusive (t : Terms) (now : Nat) :
    ¬ (now < t.deadline ∧ t.deadline ≤ now) := by
  omega

theorem conservation (t : Terms) (l : Ledger) (c : Call) :
    total (fixedTransition t l c) = total l := by
  cases hop : c.operation
  · by_cases h : c.caller = t.buyer ∧ c.now < t.deadline ∧ l.state = .funded
    · simp [fixedTransition, hop, h, total, Nat.add_comm]
    · simp [fixedTransition, hop, h]
  · by_cases h : c.caller = t.buyer ∧ t.deadline ≤ c.now ∧ l.state = .funded
    · simp [fixedTransition, hop, h, total, Nat.add_comm, Nat.add_left_comm]
    · simp [fixedTransition, hop, h]

theorem defective_origin_counterexample :
    let t : Terms := {
      buyer := 1, seller := 2, amount := 10, deployedAt := 0, deadline := 5,
      buyer_ne_seller := by decide, buyer_nonzero := by decide,
      seller_nonzero := by decide, amount_positive := by decide,
      deadline_after_deployment := by decide }
    let c : Call := { operation := .release, caller := 3, origin := 1, now := 4 }
    (defectiveTransition t (initialLedger t) c).state = .released ∧
    fixedTransition t (initialLedger t) c = initialLedger t := by
  decide

end MantiQEscrow
