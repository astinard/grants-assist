# TestFlight Setup Guide for GrantsAssist

## Prerequisites

1. **Apple Developer Program membership** ($99/year)
   - Enroll at: https://developer.apple.com/programs/enroll/

2. **Xcode with valid Apple ID signed in**
   - Xcode > Settings > Accounts > Add Apple ID

## Step 1: Get Your Team ID

1. Go to https://developer.apple.com/account
2. Click "Membership" in the sidebar
3. Copy your **Team ID** (10-character string like "ABC123DEF4")

## Step 2: Update Project Configuration

Update `project.yml` with your Team ID:

```yaml
settings:
  base:
    DEVELOPMENT_TEAM: "YOUR_TEAM_ID_HERE"
```

Then regenerate the Xcode project:

```bash
cd ios-app
xcodegen generate
```

## Step 3: Create App in App Store Connect

1. Go to https://appstoreconnect.apple.com
2. Click "My Apps" > "+" > "New App"
3. Fill in:
   - Platform: iOS
   - Name: GrantsAssist
   - Primary Language: English (US)
   - Bundle ID: com.grantsassist.app
   - SKU: grantsassist-ios-001

## Step 4: Configure Signing

### Option A: Automatic Signing (Recommended for solo developers)

1. Open `GrantsAssist.xcodeproj` in Xcode
2. Select the GrantsAssist target
3. Go to "Signing & Capabilities"
4. Check "Automatically manage signing"
5. Select your Team

### Option B: Manual Signing with Fastlane Match

```bash
# Initialize match (first time only)
cd ios-app
bundle install
bundle exec fastlane match init

# Create certificates and profiles
bundle exec fastlane match appstore
bundle exec fastlane match development
```

## Step 5: Build and Upload to TestFlight

### Using Fastlane (Recommended)

```bash
cd ios-app

# Set environment variables
export APPLE_ID="your-apple-id@example.com"
export TEAM_ID="YOUR_TEAM_ID"
export ITC_TEAM_ID="YOUR_ITC_TEAM_ID"  # Usually same as TEAM_ID

# Install dependencies
bundle install

# Upload to TestFlight
bundle exec fastlane beta
```

### Using Xcode

1. Open `GrantsAssist.xcodeproj`
2. Select "Any iOS Device (arm64)" as the build target
3. Product > Archive
4. In the Organizer window, click "Distribute App"
5. Select "App Store Connect" > "Upload"
6. Follow the prompts to upload

## Step 6: Configure TestFlight

1. Go to https://appstoreconnect.apple.com
2. Select your app > TestFlight tab
3. Wait for build processing (5-30 minutes)
4. Once processed, click the build
5. Add test information:
   - What to Test: "Test grant discovery, registration, and application features"
   - Beta App Description: Brief app description
6. Add testers:
   - Internal Testing: Add Apple IDs from your team
   - External Testing: Create a group and add email addresses

## Step 7: Invite Testers

### Internal Testers (up to 100)
- Must have App Store Connect access
- Builds available immediately after processing

### External Testers (up to 10,000)
- Just need an email address
- Requires Beta App Review (usually 24-48 hours for first build)

## Environment Variables

Create a `.env` file (don't commit to git):

```bash
APPLE_ID=your-apple-id@example.com
TEAM_ID=YOUR_TEAM_ID
ITC_TEAM_ID=YOUR_ITC_TEAM_ID
FASTLANE_PASSWORD=your-apple-id-password
FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

Generate an app-specific password at: https://appleid.apple.com/account/manage

## Troubleshooting

### "No signing certificate" error
- Xcode > Settings > Accounts > Manage Certificates > Add (+)

### "Provisioning profile doesn't include signing certificate"
- Delete old profiles: ~/Library/MobileDevice/Provisioning Profiles/
- Let Xcode regenerate them

### Build rejected for missing icons
- Ensure AppIcon asset catalog has all required sizes
- Use https://appicon.co to generate icon set

### "App ID not found" error
- Create the App ID at https://developer.apple.com/account/resources/identifiers
- Bundle ID: com.grantsassist.app

## Quick Commands

```bash
# Build and upload to TestFlight
bundle exec fastlane beta

# Run tests before uploading
bundle exec fastlane test

# Increment version for new release
bundle exec fastlane release
```
