import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authService: AuthService
    @State private var showingSignOutAlert = false

    var body: some View {
        NavigationStack {
            List {
                // Account Section
                Section("Account") {
                    if let user = authService.currentUser {
                        HStack {
                            Image(systemName: "person.circle.fill")
                                .font(.title)
                                .foregroundStyle(.secondary)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(user.email)
                                    .font(.headline)

                                HStack(spacing: 4) {
                                    Image(systemName: subscriptionIcon(for: user.subscriptionTier))
                                    Text(user.subscriptionTier.displayName)
                                }
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 8)
                    }
                }

                // Subscription Section
                Section("Subscription") {
                    NavigationLink {
                        SubscriptionView()
                    } label: {
                        HStack {
                            Image(systemName: "crown.fill")
                                .foregroundStyle(.yellow)
                            Text("Manage Subscription")
                        }
                    }

                    if let user = authService.currentUser {
                        HStack {
                            Text("Current Plan")
                            Spacer()
                            Text(user.subscriptionTier.displayName)
                                .foregroundStyle(.secondary)
                        }

                        HStack {
                            Text("Applications/Month")
                            Spacer()
                            Text("\(user.subscriptionTier.applicationsPerMonth == Int.max ? "Unlimited" : "\(user.subscriptionTier.applicationsPerMonth)")")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                // Support Section
                Section("Support") {
                    Link(destination: URL(string: "https://grantsassist.com/help")!) {
                        HStack {
                            Image(systemName: "questionmark.circle")
                            Text("Help Center")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundStyle(.secondary)
                        }
                    }

                    Link(destination: URL(string: "mailto:support@grantsassist.com")!) {
                        HStack {
                            Image(systemName: "envelope")
                            Text("Contact Support")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                // Legal Section
                Section("Legal") {
                    Link(destination: URL(string: "https://grantsassist.com/privacy")!) {
                        HStack {
                            Image(systemName: "hand.raised")
                            Text("Privacy Policy")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundStyle(.secondary)
                        }
                    }

                    Link(destination: URL(string: "https://grantsassist.com/terms")!) {
                        HStack {
                            Image(systemName: "doc.text")
                            Text("Terms of Service")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                // App Info Section
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("\(Configuration.appVersion) (\(Configuration.buildNumber))")
                            .foregroundStyle(.secondary)
                    }
                }

                // Sign Out
                Section {
                    Button(role: .destructive) {
                        showingSignOutAlert = true
                    } label: {
                        HStack {
                            Spacer()
                            Text("Sign Out")
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .alert("Sign Out", isPresented: $showingSignOutAlert) {
                Button("Cancel", role: .cancel) {}
                Button("Sign Out", role: .destructive) {
                    authService.signOut()
                }
            } message: {
                Text("Are you sure you want to sign out?")
            }
        }
    }

    private func subscriptionIcon(for tier: SubscriptionTier) -> String {
        switch tier {
        case .free: return "person"
        case .pro: return "star"
        case .business: return "building.2"
        }
    }
}

// MARK: - Subscription View

struct SubscriptionView: View {
    @EnvironmentObject var authService: AuthService

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header
                VStack(spacing: 8) {
                    Image(systemName: "crown.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(.yellow)

                    Text("Upgrade Your Plan")
                        .font(.title)
                        .fontWeight(.bold)

                    Text("Get more applications and premium features")
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 32)

                // Plans
                VStack(spacing: 16) {
                    PlanCard(
                        tier: .free,
                        isCurrentPlan: authService.currentUser?.subscriptionTier == .free
                    )

                    PlanCard(
                        tier: .pro,
                        isCurrentPlan: authService.currentUser?.subscriptionTier == .pro
                    )

                    PlanCard(
                        tier: .business,
                        isCurrentPlan: authService.currentUser?.subscriptionTier == .business
                    )
                }
                .padding(.horizontal)

                // Restore Purchases
                Button {
                    // TODO: Restore purchases via StoreKit
                } label: {
                    Text("Restore Purchases")
                        .font(.subheadline)
                }
                .padding(.bottom, 32)
            }
        }
        .navigationTitle("Subscription")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Plan Card

struct PlanCard: View {
    let tier: SubscriptionTier
    let isCurrentPlan: Bool

    var body: some View {
        VStack(spacing: 16) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(tier.displayName)
                        .font(.title2)
                        .fontWeight(.bold)

                    Text(tier.price)
                        .font(.headline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                if isCurrentPlan {
                    Text("Current")
                        .font(.caption)
                        .fontWeight(.medium)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.green.opacity(0.15))
                        .foregroundStyle(.green)
                        .cornerRadius(12)
                }
            }

            Divider()

            // Features
            VStack(alignment: .leading, spacing: 8) {
                FeatureRow(
                    text: tier.applicationsPerMonth == Int.max ? "Unlimited applications" : "\(tier.applicationsPerMonth) application\(tier.applicationsPerMonth == 1 ? "" : "s")/month"
                )

                if tier != .free {
                    FeatureRow(text: "AI-powered narratives")
                    FeatureRow(text: "PDF generation")
                    FeatureRow(text: "Priority support")
                }

                if tier == .business {
                    FeatureRow(text: "Multi-user access")
                    FeatureRow(text: "Custom branding")
                }
            }

            // CTA
            if !isCurrentPlan && tier != .free {
                Button {
                    // TODO: Purchase via StoreKit
                } label: {
                    Text("Upgrade to \(tier.displayName)")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.accentColor)
                        .foregroundStyle(.white)
                        .cornerRadius(12)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(isCurrentPlan ? Color.green : Color(.systemGray5), lineWidth: isCurrentPlan ? 2 : 1)
        )
    }
}

struct FeatureRow: View {
    let text: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
            Text(text)
                .font(.subheadline)
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AuthService.shared)
}
