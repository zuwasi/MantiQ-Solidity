// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

interface IRelease { function release() external; }

/// @notice Test-only intermediary. The buyer calls this, not the escrow directly.
contract Intermediary {
    function forward(address escrow) external { IRelease(escrow).release(); }
}

contract RejectingSupplier {
    receive() external payable { revert("no payment accepted"); }
}
