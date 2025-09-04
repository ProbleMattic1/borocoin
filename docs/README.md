
# Township Rewards • Starter Kit (v3: Easy Wins)

Local, gas-free **closed-loop rewards** prototype. This version adds:
- **QR codes** for users + **camera QR scanner** for merchants.
- **Rate limits & daily caps** per merchant with **basic alerts**.
- **Settlement CSV export** for admin.
- Optional **point expiry** policy.

## Quick Start (Windows)
1. Install **Python 3.10+**.
2. Double-click `scripts\run.bat`.
3. Visit **http://localhost:8000**.
4. Login as `admin`, `merchant1`, or `user1` etc.
5. Try: Admin **Issue**, Merchant **EARN/REDEEM**, User **Show QR**, Merchant **Scan QR**.

## Admin Features
- **Settings**: set `expiry_days` and run expiry.
- **Merchant caps**: rate/min, daily earn/redeem caps.
- **Reports**: download settlement CSV by date range.
- **Anchors**: compute daily Merkle root over tx hashes.

## Data Integrity
- Transactions are hash-chained (`prev_hash` → `thash`), with **daily Merkle root** (`/anchor/daily`).

## Upgrade Path
- Replace local ledger with a private **PoA** chain; use `contracts/RestrictedPoints.sol`.

