import Foundation

enum Configuration {
    // MARK: - API Configuration

    #if DEBUG
    static let apiBaseURL = URL(string: "http://localhost:8002")!
    #else
    static let apiBaseURL = URL(string: "https://api.grantsassist.com")!
    #endif

    static let apiVersion = "v1"

    // MARK: - Keychain Keys
    enum KeychainKey {
        static let accessToken = "com.grantsassist.accessToken"
        static let refreshToken = "com.grantsassist.refreshToken"
        static let userId = "com.grantsassist.userId"
    }

    // MARK: - RevenueCat
    static let revenueCatAPIKey = "your_revenuecat_api_key"

    // MARK: - App Info
    static let appName = "GrantsAssist"
    static let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    static let buildNumber = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"

    // MARK: - Feature Flags
    enum Features {
        static let enableOfflineMode = false
        static let enablePushNotifications = true
        static let enableAnalytics = true
    }

    // MARK: - Subscription Tiers
    enum SubscriptionLimits {
        static let freeApplicationsPerMonth = 1
        static let proApplicationsPerMonth = 10
        static let businessApplicationsPerMonth = Int.max
    }
}
