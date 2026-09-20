#!/usr/bin/env wolframscript

args = Rest[$ScriptCommandLine];
outputPath = If[Length[args] >= 1, Last[args], FileNameJoin[{DirectoryName[$InputFileName], "result.json"}]];

states = {"Funded", "Released", "Refunded"};
operations = {"Release", "Refund"};
buyer = 1; seller = 2; amount = 10; deadline = 5;
callers = {0, buyer, seller, 3}; origins = {0, buyer, seller, 3};
times = {deadline - 1, deadline, deadline + 1};

initial = <|"State" -> "Funded", "Escrow" -> amount,
  "SellerReceived" -> 0, "BuyerReceived" -> 0|>;

transition[variant_, ledger_, operation_, caller_, origin_, now_] := Module[
  {releaseAuth},
  releaseAuth = If[variant === "Defective", origin === buyer, caller === buyer];
  Which[
    operation === "Release" && releaseAuth && now < deadline && ledger["State"] === "Funded",
      <|"State" -> "Released", "Escrow" -> 0,
        "SellerReceived" -> ledger["SellerReceived"] + ledger["Escrow"],
        "BuyerReceived" -> ledger["BuyerReceived"]|>,
    operation === "Refund" && caller === buyer && now >= deadline && ledger["State"] === "Funded",
      <|"State" -> "Refunded", "Escrow" -> 0,
        "SellerReceived" -> ledger["SellerReceived"],
        "BuyerReceived" -> ledger["BuyerReceived"] + ledger["Escrow"]|>,
    True, ledger
  ]
];

total[ledger_] := ledger["Escrow"] + ledger["SellerReceived"] + ledger["BuyerReceived"];
ledgers = Flatten[Table[
  <|"State" -> state, "Escrow" -> escrow, "SellerReceived" -> sr, "BuyerReceived" -> br|>,
  {state, states}, {escrow, 0, 2}, {sr, 0, 2}, {br, 0, 2}], 3];
cases = Flatten[Table[{ledger, operation, caller, origin, now}, {ledger, ledgers},
  {operation, operations}, {caller, callers}, {origin, origins}, {now, times}], 4];

unauthorizedOK = And @@ (Function[x,
  With[{l = x[[1]], op = x[[2]], caller = x[[3]], origin = x[[4]], now = x[[5]]},
    op =!= "Release" || caller === buyer || transition["Fixed", l, op, caller, origin, now] === l]] /@ cases);
terminalOK = And @@ (Function[x,
  With[{l = x[[1]], op = x[[2]], caller = x[[3]], origin = x[[4]], now = x[[5]]},
    l["State"] === "Funded" || transition["Fixed", l, op, caller, origin, now] === l]] /@ cases);
conservationOK = And @@ (Function[x,
  total[transition["Fixed", x[[1]], x[[2]], x[[3]], x[[4]], x[[5]]]] === total[x[[1]]] ] /@ cases);
failedCallsOK = And @@ (Function[x, With[
  {l = x[[1]], op = x[[2]], caller = x[[3]], origin = x[[4]], now = x[[5]]},
  With[{enabled = (op === "Release" && caller === buyer && now < deadline && l["State"] === "Funded") ||
      (op === "Refund" && caller === buyer && now >= deadline && l["State"] === "Funded")},
    enabled || transition["Fixed", l, op, caller, origin, now] === l]]] /@ cases);
timeExclusiveOK = And @@ (Not[# < deadline && # >= deadline] & /@ times);

boundaryActual = Association@Table[ToString[now] -> <|
  "ReleaseState" -> transition["Fixed", initial, "Release", buyer, buyer, now]["State"],
  "RefundState" -> transition["Fixed", initial, "Refund", buyer, buyer, now]["State"]|>, {now, times}];
boundaryExpected = <|
  ToString[deadline - 1] -> <|"ReleaseState" -> "Released", "RefundState" -> "Funded"|>,
  ToString[deadline] -> <|"ReleaseState" -> "Funded", "RefundState" -> "Refunded"|>,
  ToString[deadline + 1] -> <|"ReleaseState" -> "Funded", "RefundState" -> "Refunded"|>|>;
boundaryOK = boundaryActual === boundaryExpected;

(* Search feasible nonzero identities for a caller/origin authorization mismatch. *)
candidateCalls = Tuples[{{3, buyer, seller}, {buyer, seller, 3}, times}];
found = SelectFirst[candidateCalls,
  (#[[1]] =!= buyer &&
    transition["Defective", initial, "Release", #[[1]], #[[2]], #[[3]]]["State"] === "Released" &&
    transition["Fixed", initial, "Release", #[[1]], #[[2]], #[[3]]] === initial) &,
  Missing["NoCounterexample"]];
If[MissingQ[found], Print["FAIL: no defective counterexample found"]; Exit[1]];
witness = <|"Buyer" -> buyer, "Seller" -> seller, "Caller" -> found[[1]], "Origin" -> found[[2]],
  "Now" -> found[[3]], "Deadline" -> deadline|>;
defectiveState = transition["Defective", initial, "Release", witness["Caller"], witness["Origin"], witness["Now"]]["State"];
fixedState = transition["Fixed", initial, "Release", witness["Caller"], witness["Origin"], witness["Now"]]["State"];
counterexampleOK = defectiveState === "Released" && fixedState === "Funded";

checks = <|"UnauthorizedReleaseRejected" -> unauthorizedOK,
  "FailedCallsUnchanged" -> failedCallsOK, "TerminalAbsorbing" -> terminalOK,
  "ReleaseRefundTimeExclusive" -> timeExclusiveOK, "Conservation" -> conservationOK,
  "BoundaryChecks" -> boundaryOK, "DefectiveCounterexampleFound" -> counterexampleOK|>;
result = <|
  "Environment" -> <|"Version" -> $Version, "VersionNumber" -> $VersionNumber,
    "System" -> $System, "ProcessorType" -> $ProcessorType|>,
  "ModelParameters" -> <|"Buyer" -> buyer, "Seller" -> seller, "Amount" -> amount,
    "DeploymentTimestamp" -> 0, "Deadline" -> deadline|>,
  "Search" -> <|"CaseCount" -> Length[cases], "States" -> states,
    "Callers" -> callers, "Origins" -> origins, "Times" -> times|>,
  "Checks" -> checks, "BoundaryEvidence" -> boundaryActual,
  "DefectiveCounterexample" -> Join[witness, <|"DefectiveState" -> defectiveState,
    "FixedState" -> fixedState|>], "AllPassed" -> And @@ Values[checks]|>;

Export[outputPath, result, "RawJSON"];
Print["Wrote " <> ExpandFileName[outputPath]];
Print["Checks: " <> ToString[checks, InputForm]];
If[!TrueQ[result["AllPassed"]], Exit[1]];
Exit[0];
