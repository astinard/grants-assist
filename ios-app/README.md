# GrantsAssist iOS App

A SwiftUI iOS application for discovering and applying for grants.

## Setup Instructions

Since Xcode project files are complex, follow these steps to create your project:

### Option 1: Create Project in Xcode (Recommended)

1. **Open Xcode** and select "Create New Project"

2. **Choose Template:**
   - Select "iOS" → "App"
   - Click "Next"

3. **Configure Project:**
   - Product Name: `GrantsAssist`
   - Team: Select your Apple Developer team
   - Organization Identifier: `com.yourcompany`
   - Interface: `SwiftUI`
   - Language: `Swift`
   - Storage: `None`
   - Uncheck "Include Tests" (add later)

4. **Save Location:**
   - Save to the `ios-app` folder
   - This will create the `.xcodeproj` file

5. **Add Source Files:**
   - Delete the default `ContentView.swift` and `GrantsAssistApp.swift`
   - Drag the `GrantsAssist` folder into your project in Xcode
   - Make sure "Copy items if needed" is UNCHECKED
   - Select "Create groups"

6. **Configure Signing:**
   - Select the project in the navigator
   - Go to "Signing & Capabilities"
   - Add your team and bundle identifier
   - Add capability: "Sign in with Apple"

7. **Set Deployment Target:**
   - Set to iOS 16.0 or later

### Option 2: Use Swift Package (Alternative)

Create a `Package.swift` at the project root and use SPM for dependencies.

## Project Structure

```
GrantsAssist/
├── App/
│   ├── GrantsAssistApp.swift    # App entry point
│   ├── RootView.swift           # Root navigation
│   └── Configuration.swift      # App configuration
├── Core/
│   ├── Network/
│   │   ├── APIClient.swift      # HTTP client
│   │   └── Endpoints.swift      # API endpoints
│   ├── Models/
│   │   ├── User.swift           # User & auth models
│   │   ├── Grant.swift          # Grant program models
│   │   ├── Application.swift    # Application models
│   │   └── Eligibility.swift    # Eligibility models
│   └── Services/
│       ├── AuthService.swift    # Authentication
│       └── KeychainService.swift # Secure storage
├── Features/
│   ├── Auth/                    # Sign in screens
│   ├── Discovery/               # Grant browsing
│   ├── Applications/            # Application management
│   ├── Profile/                 # User profile
│   ├── Eligibility/             # Eligibility checking
│   └── Settings/                # App settings
└── Shared/
    ├── Components/              # Reusable UI
    └── Extensions/              # Swift extensions
```

## Features

- **Apple Sign-In** - Native authentication
- **Grant Discovery** - Browse and search programs
- **Eligibility Matching** - See your match score
- **Application Management** - Track your applications
- **Profile Management** - Reusable application data
- **Subscription Tiers** - Free, Pro, Business

## Requirements

- iOS 16.0+
- Xcode 15.0+
- Swift 5.9+
- Apple Developer account (for Sign in with Apple)

## Backend Configuration

Update `Configuration.swift` with your backend URL:

```swift
#if DEBUG
static let apiBaseURL = URL(string: "http://localhost:8000")!
#else
static let apiBaseURL = URL(string: "https://api.grantsassist.com")!
#endif
```

## Running the Backend

```bash
cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Capabilities Required

Add these in Xcode under "Signing & Capabilities":

1. **Sign in with Apple** - For authentication
2. **Keychain Sharing** (optional) - For token persistence

## App Store Submission

Before submitting:

1. Update bundle identifier
2. Add app icons to `Assets.xcassets/AppIcon.appiconset`
3. Update `Configuration.swift` with production API URL
4. Add RevenueCat API key for subscriptions
5. Complete App Store Connect listing
