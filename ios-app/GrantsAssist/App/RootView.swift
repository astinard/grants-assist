import SwiftUI

struct RootView: View {
    @EnvironmentObject var authService: AuthService
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            if authService.isAuthenticated {
                MainTabView()
            } else {
                AuthView()
            }
        }
        .animation(.easeInOut, value: authService.isAuthenticated)
    }
}

struct MainTabView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        TabView(selection: $appState.selectedTab) {
            DiscoveryView()
                .tabItem {
                    Label("Discover", systemImage: "magnifyingglass")
                }
                .tag(AppState.Tab.discover)

            ApplicationsListView()
                .tabItem {
                    Label("Applications", systemImage: "doc.text")
                }
                .tag(AppState.Tab.applications)

            ProfileView()
                .tabItem {
                    Label("Profile", systemImage: "person.circle")
                }
                .tag(AppState.Tab.profile)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape")
                }
                .tag(AppState.Tab.settings)
        }
        .tint(.accentColor)
    }
}

#Preview {
    RootView()
        .environmentObject(AuthService.shared)
        .environmentObject(AppState())
}
