// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

/// @notice Educational, single-milestone escrow. NOT audited for production use.
contract Escrow {
    enum State { Funded, Released, Refunded }
    address payable public immutable buyer;
    address payable public immutable seller;
    uint256 public immutable deadline;
    State public state;

    event Settled(State state, address recipient, uint256 amount);

    constructor(address payable supplier, uint256 due) payable {
        require(supplier != address(0) && supplier != msg.sender, "invalid supplier");
        require(msg.value > 0 && due > block.timestamp, "invalid terms");
        buyer = payable(msg.sender);
        seller = supplier;
        deadline = due;
    }

    function releaseAuthorized() internal view virtual returns (bool) {
        return msg.sender == buyer;
    }

    function release() external {
        require(releaseAuthorized(), "buyer only");
        require(state == State.Funded, "already settled");
        require(block.timestamp < deadline, "release expired");
        settle(State.Released, seller);
    }

    function refund() external {
        require(msg.sender == buyer, "buyer only");
        require(state == State.Funded, "already settled");
        require(block.timestamp >= deadline, "refund premature");
        settle(State.Refunded, buyer);
    }

    function settle(State next, address payable recipient) private {
        state = next;
        uint256 amount = address(this).balance;
        (bool ok,) = recipient.call{value: amount}("");
        require(ok, "payment failed");
        emit Settled(next, recipient, amount);
    }
}
