# 🏙️ BoroCoin - Township Rewards System

A **closed-loop digital rewards platform** designed for local townships and communities. BoroCoin enables businesses to issue and redeem loyalty points in a secure, transparent, and community-focused ecosystem.

## 🎯 Project Overview

BoroCoin is a comprehensive rewards system that combines traditional loyalty program features with modern blockchain-inspired security. It's designed to strengthen local economies by keeping value circulating within the community while providing businesses with powerful tools to engage customers.

### Key Features

- **🔐 Closed-Loop System**: Points can only be earned from and redeemed at participating local merchants
- **📱 QR Code Integration**: Seamless customer identification and transaction processing
- **🛡️ Fraud Prevention**: Rate limiting, daily caps, and anomaly detection
- **📊 Administrative Dashboard**: Complete oversight with reporting and analytics
- **⛓️ Data Integrity**: Hash-chained transactions with daily Merkle root anchoring
- **📈 Settlement System**: Automated merchant settlement and CSV export capabilities
- **⏰ Point Expiry**: Configurable expiration policies to encourage active usage

## 🏗️ Architecture

### Backend (FastAPI)
- **Technology**: FastAPI with Python 3.10+
- **Database**: SQLite for local development (easily upgradeable to PostgreSQL)
- **Authentication**: JWT-based with role-based access control
- **Security**: HMAC-signed QR codes, transaction hash chains

### Smart Contracts (Solidity)
- **RestrictedPoints.sol**: ERC-20 compatible token with transfer restrictions
- **Upgrade Path**: Ready for deployment on Proof-of-Authority (PoA) networks

### Frontend
- **Single-Page Application**: Vanilla JavaScript with modern UI
- **Camera Integration**: QR code scanning for merchants
- **Real-time Updates**: Live transaction monitoring and balance updates

## 👥 User Roles

### 🔑 Admin
- Issue points directly to users
- Configure system settings (expiry policies, merchant caps)
- Generate settlement reports and CSV exports
- Create daily Merkle root anchors for audit trails
- Monitor system alerts and anomalies

### 🏪 Merchant
- Award points to customers for purchases (EARN transactions)
- Accept points as payment (REDEEM transactions)
- Scan customer QR codes for identification
- View merchant balance and transaction history
- Subject to configurable rate limits and daily caps

### 👤 User/Customer
- Generate time-limited QR codes for identification
- Check point balance and transaction history
- Earn points from participating merchants
- Redeem points for goods and services

## 🚀 Quick Start

### Windows Setup
1. **Install Python 3.10+** from python.org
2. **Run the application**:
   ```bash
   # Navigate to borocoin folder
   cd borocoin
   
   # Double-click to run (or execute in terminal)
   scripts\run.bat
   ```
3. **Access the dashboard**: Open http://localhost:8000
4. **Demo Login**: Use predefined accounts:
   - `admin` - Program Administrator
   - `merchant1` - Sunny Cafe
   - `merchant2` - Hillsborough Books  
   - `user1` - Alex Johnson
   - `user2` - Sam Rivera

### Linux/Mac Setup
```bash
cd borocoin
./scripts/run.sh
```

## 📋 Core Functionality

### Transaction Types
- **EARN**: Merchants award points to customers
- **REDEEM**: Customers spend points at merchants
- **ISSUE**: Admin creates new points (minting)
- **EXPIRE**: Automatic point expiration based on policy
- **ADJUST**: Administrative balance adjustments

### Security Features
- **Rate Limiting**: Configurable transactions per minute per merchant
- **Daily Caps**: Maximum daily earn/redeem amounts per merchant
- **Fraud Detection**: Rapid redemption pattern monitoring
- **Data Integrity**: SHA-256 hash chains linking all transactions
- **Audit Trail**: Daily Merkle root generation for immutable records

### Administrative Tools
- **Settlement Reports**: CSV export for merchant payouts
- **Merchant Configuration**: Individual caps and limits per business
- **System Alerts**: Automated notifications for suspicious activity
- **Point Expiry Management**: FIFO-based expiration processing

## 🗂️ Project Structure

```
borocoin/
├── backend/
│   ├── app.py              # FastAPI application core
│   ├── requirements.txt    # Python dependencies
│   ├── static/            # Static web assets
│   └── templates/
│       └── index.html     # Single-page application UI
├── contracts/
│   └── RestrictedPoints.sol # ERC-20 token contract
├── docs/
│   ├── README.md          # Technical documentation
│   ├── ROADMAP.md         # Development roadmap
│   ├── GOVERNANCE.md      # Governance structure
│   ├── NEXT_STEPS.md      # Implementation guide
│   └── PROGRAM_TERMS_TEMPLATE.md # Legal template
├── scripts/
│   ├── run.bat/.sh        # Application launcher
│   └── reset_db.bat/.sh   # Database reset utility
└── README.md              # This file
```

## 🛠️ Technical Implementation

### Database Schema
- **users**: User accounts and roles
- **merchants**: Business accounts and configurations
- **accounts**: Balance tracking for all entities
- **transactions**: Complete transaction history with hash chains
- **anchors**: Daily Merkle root storage
- **alerts**: Security and anomaly notifications
- **settings**: System configuration

### API Endpoints
- **Authentication**: `/auth/login`, `/me`
- **Transactions**: `/earn`, `/redeem`, `/admin/issue`
- **Balances**: `/balance/{account_id}`, `/merchant/balance`
- **QR Codes**: `/qr/user/{uid}`, `/qr/verify`
- **Administration**: `/admin/settings`, `/admin/settlement.csv`
- **Anchoring**: `/anchor/daily`

## 🔮 Roadmap & Future Development

### Phase 1: MVP (Current)
- ✅ Local ledger with role-based access
- ✅ Core transaction types (EARN/REDEEM/ISSUE)
- ✅ Basic reporting and daily anchors

### Phase 2: Pilot Ready
- ✅ QR code generation and scanning
- ✅ Settlement export capabilities
- ✅ Fraud detection and alerts

### Phase 3: Production Hardening
- ✅ Rate limiting and merchant caps
- ✅ Point expiry policies
- 🔄 Point-of-sale system webhooks
- 🔄 Proof-of-Authority blockchain deployment

### Phase 4: Advanced Features (Planned)
- 📋 Multi-tenant support for multiple townships
- 📋 Mobile applications (iOS/Android)
- 📋 Advanced analytics and business intelligence
- 📋 Integration with existing POS systems
- 📋 Automated marketing and promotional tools

## 🤝 Governance Model

### Stakeholders
- **Township Government**: Primary oversight and policy setting
- **Local Library**: Community access point and digital literacy
- **Chamber of Commerce**: Business liaison and merchant onboarding
- **Anchor Merchants**: Key businesses providing system stability

### Controls & Compliance
- Configurable rate limits and transaction caps
- Comprehensive audit trails and reporting
- Automated anomaly detection and alerting
- Regular backup and disaster recovery procedures
- Privacy protection and data security measures

## 🔧 Development & Deployment

### Dependencies
- **Python 3.10+** with FastAPI, SQLite, JWT support
- **Modern Web Browser** with camera access for QR scanning
- **Optional**: Node.js for advanced frontend development

### Environment Variables
- `JWT_SECRET`: Secret key for token signing (change in production)
- `DB_PATH`: Database file location (default: rewards.db)

### Production Considerations
- Replace SQLite with PostgreSQL for production scale
- Implement proper SSL/TLS encryption
- Set up automated backups and monitoring
- Configure proper JWT secret management
- Deploy behind reverse proxy (nginx/Apache)

## 📄 License & Legal

This is a **starter kit** and **proof of concept**. Points have no cash value and are non-transferable outside the system. Intended for local testing and community pilot programs.

For production deployment, consult with legal counsel regarding:
- Consumer protection compliance
- Financial services regulations  
- Data privacy requirements (GDPR, CCPA, etc.)
- Local business licensing requirements

## 🆘 Support & Contributing

This project is designed to be community-driven and easily customizable for different townships and regions. 

### Getting Help
- Review the `/docs` folder for detailed technical documentation
- Check the issue tracker for known problems and solutions
- Consult the roadmap for planned features and timelines

### Contributing
- Fork the repository and create feature branches
- Follow existing code style and documentation standards
- Submit pull requests with clear descriptions of changes
- Report bugs and suggest improvements through issues

---

**Built for communities, by communities.** 🏘️

*BoroCoin strengthens local economies by keeping value local and making loyalty rewards transparent, secure, and community-focused.*