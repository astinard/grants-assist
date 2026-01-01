import SwiftUI

@main
struct GrantsAssistApp: App {
    @StateObject private var authService = AuthService.shared
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authService)
                .environmentObject(appState)
        }
    }
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
