// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
import "./Escrow.sol";

/// @notice INTENTIONALLY VULNERABLE teaching fixture. Never deploy with real funds.
contract DefectiveEscrow is Escrow {
    constructor(address payable supplier, uint256 due) payable Escrow(supplier, due) {}

    function releaseAuthorized() internal view override returns (bool) {
        return tx.origin == buyer; // Deliberate CWE-346 authorization defect.
    }
}
