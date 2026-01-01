import SwiftUI
import AuthenticationServices

struct AuthView: View {
    @EnvironmentObject var authService: AuthService
    @State private var showEmailSignIn = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                // Logo and Tagline
                VStack(spacing: 16) {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.system(size: 80))
                        .foregroundStyle(Color.accentColor)

                    Text("GrantsAssist")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Find and apply for grants\nthat match your needs")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }

                Spacer()

                // Sign-In Buttons
                VStack(spacing: 16) {
                    // Apple Sign-In
                    SignInWithAppleButton(
                        onRequest: { request in
                            request.requestedScopes = [.fullName, .email]
                        },
                        onCompletion: { result in
                            Task {
                                await authService.handleAppleSignIn(result: result)
                            }
                        }
                    )
                    .signInWithAppleButtonStyle(.black)
                    .frame(height: 50)
                    .cornerRadius(12)

                    // Email Sign-In Option
                    Button {
                        showEmailSignIn = true
                    } label: {
                        HStack {
                            Image(systemName: "envelope.fill")
                            Text("Continue with Email")
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color(.systemGray5))
                        .foregroundStyle(.primary)
                        .cornerRadius(12)
                    }
                }
                .padding(.horizontal, 24)
                .disabled(authService.isLoading)

                // Error Message
                if let error = authService.error {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                // Loading Indicator
                if authService.isLoading {
                    ProgressView()
                        .padding()
                }

                Spacer()

                // Terms
                Text("By continuing, you agree to our Terms of Service and Privacy Policy")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
                    .padding(.bottom, 16)
            }
            .sheet(isPresented: $showEmailSignIn) {
                EmailAuthView()
            }
        }
    }
}

#Preview {
    AuthView()
        .environmentObject(AuthService.shared)
}
