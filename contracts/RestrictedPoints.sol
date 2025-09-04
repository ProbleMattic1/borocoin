// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * Restricted, closed-loop "points" token.
 * - Admin can mint/burn
 * - Transfers are disabled except: user -> merchant (redeem)
 * - No allowances
 */
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract RestrictedPoints is ERC20, Ownable {
    mapping(address => bool) public isMerchant;
    mapping(address => bool) public isUser;

    constructor(string memory name_, string memory symbol_) ERC20(name_, symbol_) Ownable(msg.sender) {}

    function setMerchant(address a, bool v) external onlyOwner { isMerchant[a] = v; }
    function setUser(address a, bool v) external onlyOwner { isUser[a] = v; }

    function mint(address to, uint256 amount) external onlyOwner {
        require(isUser[to] || isMerchant[to], "not enrolled");
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external onlyOwner {
        _burn(from, amount);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(isUser[from] && isMerchant[to], "transfer not allowed");
        }
        super._update(from, to, value);
    }
}
