import SwiftUI
import UserNotifications

@main
struct GrantsAssistApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var authService = AuthService.shared
    @StateObject private var appState = AppState()
    @StateObject private var notificationService = NotificationService.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authService)
                .environmentObject(appState)
                .environmentObject(notificationService)
                .onReceive(NotificationCenter.default.publisher(for: .didTapDeadlineReminder)) { notification in
                    handleDeadlineReminderTap(notification)
                }
                .task {
                    await notificationService.checkAuthorizationStatus()
                }
        }
    }

    private func handleDeadlineReminderTap(_ notification: Notification) {
        guard let grantId = notification.userInfo?["grantId"] as? String else { return }
        // Navigate to grant details
        appState.selectedTab = .discover
        // Post notification to navigate to specific grant
        NotificationCenter.default.post(
            name: .navigateToGrant,
            object: nil,
            userInfo: ["grantId": grantId]
        )
    }
}

// MARK: - App Delegate
class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Set notification delegate
        UNUserNotificationCenter.current().delegate = NotificationService.shared
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        NotificationService.shared.didRegisterForRemoteNotifications(deviceToken: deviceToken)
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        NotificationService.shared.didFailToRegisterForRemoteNotifications(error: error)
    }
}

// MARK: - Notification Names
extension Notification.Name {
    static let navigateToGrant = Notification.Name("navigateToGrant")
}

// MARK: - App State
@MainActor
final class AppState: ObservableObject {
    @Published var selectedTab: Tab = .discover
    @Published var isLoading = false
    @Published var errorMessage: String?

    enum Tab: Hashable {
        case discover
        case applications
        case profile
        case settings
    }

    func showError(_ message: String) {
        errorMessage = message
    }

    func clearError() {
        errorMessage = nil
    }
}
