# GrantsAssist

Consumer grant application assistance platform. Helps individuals and small organizations find and apply for grants (scholarships, small business, healthcare, etc.).

## Structure

```
grants-assist/
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── api/      # REST endpoints
│   │   ├── models/   # Database models
│   │   ├── services/ # Business logic, AI, PDFs
│   │   └── config/   # Settings
│   └── tests/
├── ios-app/          # SwiftUI iOS app (coming soon)
└── docs/
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run server
uvicorn app.main:app --reload
```

API available at: http://localhost:8000
Docs at: http://localhost:8000/docs

## Features

### MVP
- [ ] User auth (email + Apple Sign-In)
- [ ] Profile management (reusable info)
- [ ] Grant program discovery
- [ ] Eligibility checking
- [ ] Application builder
- [ ] PDF generation

### Future
- [ ] AI narrative generation
- [ ] Document upload
- [ ] Submission tracking
- [ ] iOS app with StoreKit subscriptions

## API Endpoints

- `POST /api/auth/register` - Email registration
- `POST /api/auth/token` - Login
- `POST /api/auth/apple` - Apple Sign-In
- `GET /api/users/profile` - Get profile
- `PATCH /api/users/profile` - Update profile
- `GET /api/programs` - List grant programs
- `GET /api/eligibility/check` - Check eligibility
- `POST /api/applications` - Create application
- `GET /api/applications` - List applications
