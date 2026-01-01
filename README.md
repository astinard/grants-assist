# GrantsAssist

A mobile-first platform helping individuals and small organizations discover and apply for grants.

## Overview

GrantsAssist simplifies the grant application process by:
- Matching users with relevant grant programs based on their profile
- Tracking application progress and deadlines
- Providing eligibility scoring to prioritize best-fit opportunities

## Architecture

```
grants-assist/
├── backend/          # FastAPI REST API
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── models/   # SQLAlchemy models
│   │   └── config/   # Settings
│   └── scripts/      # Database seeding
└── ios-app/          # SwiftUI iOS app
    └── GrantsAssist/
        ├── Core/     # Models, Network, Services
        ├── Features/ # Screen modules
        └── Shared/   # Reusable components
```

## Backend

FastAPI application with SQLite database.

### Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register` | Create account |
| `POST /api/auth/token` | Login |
| `POST /api/auth/apple` | Apple Sign-In |
| `GET /api/programs/` | List grant programs |
| `GET /api/programs/{id}` | Get program details |
| `GET /api/eligibility/check` | Check eligibility for all programs |
| `GET /api/eligibility/check/{id}` | Check eligibility for specific program |
| `GET /api/applications/` | List user's applications |
| `POST /api/applications/` | Start new application |
| `PATCH /api/applications/{id}` | Update application |
| `GET /api/users/profile` | Get user profile |
| `PATCH /api/users/profile` | Update profile |

## iOS App

SwiftUI app targeting iOS 17+.

### Features

- **Authentication**: Email/password and Sign in with Apple
- **Grant Discovery**: Browse and search grants by category
- **Eligibility Matching**: See match scores based on your profile
- **Applications**: Create, save drafts, and submit applications
- **Profile Management**: Organization details, federal IDs (EIN, UEI)
- **Settings**: Account management, subscription info

### Build

Open `ios-app/GrantsAssist.xcodeproj` in Xcode 15+ and run on simulator or device.

### Configuration

Update `Configuration.swift` to point to your backend:

```swift
static let apiBaseURL = URL(string: "http://localhost:8000")!
```

## Grant Categories

- Healthcare
- Small Business
- Education
- Nonprofit
- Agriculture
- Technology
- Housing
- Arts & Culture
- Environment
- Community Development

## Features

### Implemented
- [x] User auth (email + Apple Sign-In)
- [x] Profile management
- [x] Grant program discovery
- [x] Eligibility checking with match scores
- [x] Application builder
- [x] iOS app with full UI

### Planned
- [ ] AI narrative generation
- [ ] PDF generation
- [ ] Document upload
- [ ] Push notifications for deadlines
- [ ] StoreKit subscriptions

## License

MIT
