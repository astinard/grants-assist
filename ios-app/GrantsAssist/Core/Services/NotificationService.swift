import Foundation
import UserNotifications
import UIKit

/// Service for handling push notifications and local notifications
@MainActor
class NotificationService: NSObject, ObservableObject {
    static let shared = NotificationService()

    @Published var isAuthorized = false
    @Published var deviceToken: String?

    private let notificationCenter = UNUserNotificationCenter.current()

    override init() {
        super.init()
        notificationCenter.delegate = self
    }

    // MARK: - Authorization

    /// Request notification permissions from the user
    func requestAuthorization() async -> Bool {
        do {
            let options: UNAuthorizationOptions = [.alert, .badge, .sound]
            let granted = try await notificationCenter.requestAuthorization(options: options)
            isAuthorized = granted

            if granted {
                await registerForRemoteNotifications()
            }

            return granted
        } catch {
            print("Notification authorization error: \(error)")
            return false
        }
    }

    /// Check current authorization status
    func checkAuthorizationStatus() async {
        let settings = await notificationCenter.notificationSettings()
        isAuthorized = settings.authorizationStatus == .authorized
    }

    /// Register for remote (push) notifications
    private func registerForRemoteNotifications() async {
        await MainActor.run {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }

    // MARK: - Device Token

    /// Handle successful device token registration
    func didRegisterForRemoteNotifications(deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        self.deviceToken = token
        print("Device token: \(token)")

        // Register token with backend
        Task {
            await registerDeviceTokenWithBackend(token: token)
        }
    }

    /// Handle failed device token registration
    func didFailToRegisterForRemoteNotifications(error: Error) {
        print("Failed to register for remote notifications: \(error)")
    }

    /// Register device token with the backend
    private func registerDeviceTokenWithBackend(token: String) async {
        guard let _ = KeychainService.shared.getAccessToken() else {
            print("No auth token, skipping device registration")
            return
        }

        do {
            let _: EmptyResponse = try await APIClient.shared.request(
                NotificationEndpoints.registerDevice(token: token, platform: "ios")
            )
            print("Device token registered with backend")
        } catch {
            print("Failed to register device token: \(error)")
        }
    }

    // MARK: - Local Notifications

    /// Schedule a local notification for a grant deadline
    func scheduleDeadlineReminder(
        grantId: String,
        grantName: String,
        deadline: Date,
        daysBeforeDeadline: Int = 7
    ) async {
        let content = UNMutableNotificationContent()
        content.title = "Grant Deadline Approaching"
        content.body = "\(grantName) deadline is in \(daysBeforeDeadline) days. Don't miss out!"
        content.sound = .default
        content.userInfo = ["grantId": grantId, "type": "deadline_reminder"]

        // Calculate reminder date
        guard let reminderDate = Calendar.current.date(
            byAdding: .day,
            value: -daysBeforeDeadline,
            to: deadline
        ) else { return }

        // Only schedule if reminder is in the future
        guard reminderDate > Date() else { return }

        let components = Calendar.current.dateComponents(
            [.year, .month, .day, .hour, .minute],
            from: reminderDate
        )
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)

        let identifier = "deadline_\(grantId)_\(daysBeforeDeadline)d"
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)

        do {
            try await notificationCenter.add(request)
            print("Scheduled deadline reminder for \(grantName)")
        } catch {
            print("Failed to schedule notification: \(error)")
        }
    }

    /// Schedule reminders for multiple time intervals before deadline
    func scheduleDeadlineReminders(grantId: String, grantName: String, deadline: Date) async {
        // Schedule reminders at 7 days, 3 days, and 1 day before deadline
        let reminderDays = [7, 3, 1]

        for days in reminderDays {
            await scheduleDeadlineReminder(
                grantId: grantId,
                grantName: grantName,
                deadline: deadline,
                daysBeforeDeadline: days
            )
        }
    }

    /// Cancel all deadline reminders for a specific grant
    func cancelDeadlineReminders(grantId: String) {
        let identifiers = [7, 3, 1].map { "deadline_\(grantId)_\($0)d" }
        notificationCenter.removePendingNotificationRequests(withIdentifiers: identifiers)
    }

    /// Cancel all pending notifications
    func cancelAllNotifications() {
        notificationCenter.removeAllPendingNotificationRequests()
    }

    // MARK: - Badge Management

    /// Clear the app badge
    func clearBadge() async {
        await MainActor.run {
            UIApplication.shared.applicationIconBadgeNumber = 0
        }
    }
}

// MARK: - UNUserNotificationCenterDelegate

extension NotificationService: UNUserNotificationCenterDelegate {
    /// Handle notification when app is in foreground
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        // Show notification even when app is in foreground
        completionHandler([.banner, .sound, .badge])
    }

    /// Handle notification tap
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let userInfo = response.notification.request.content.userInfo

        // Handle different notification types
        if let type = userInfo["type"] as? String {
            switch type {
            case "deadline_reminder":
                if let grantId = userInfo["grantId"] as? String {
                    handleDeadlineReminderTap(grantId: grantId)
                }
            default:
                break
            }
        }

        completionHandler()
    }

    /// Handle deadline reminder notification tap
    private nonisolated func handleDeadlineReminderTap(grantId: String) {
        // Post notification to navigate to grant details
        NotificationCenter.default.post(
            name: .didTapDeadlineReminder,
            object: nil,
            userInfo: ["grantId": grantId]
        )
    }
}

// MARK: - Notification Names

extension Notification.Name {
    static let didTapDeadlineReminder = Notification.Name("didTapDeadlineReminder")
}

// MARK: - Empty Response for API calls

struct EmptyResponse: Codable {}
