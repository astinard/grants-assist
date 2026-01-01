import Foundation
import AuthenticationServices

@MainActor
final class AuthService: NSObject, ObservableObject {
    static let shared = AuthService()

    @Published private(set) var currentUser: User?
    @Published private(set) var isAuthenticated = false
    @Published private(set) var isLoading = false
    @Published var error: String?

    private let apiClient = APIClient.shared
    private let keychain = KeychainService.shared

    private override init() {
        super.init()
        #if DEBUG
        if CommandLine.arguments.contains("-testMode") {
            Task {
                await autoLoginForTesting()
            }
            return
        }
        #endif
        checkExistingSession()
    }

    #if DEBUG
    /// Auto-login with test credentials for UI testing
    private func autoLoginForTesting() async {
        let testEmail = "uitest_\(Int(Date().timeIntervalSince1970))@test.com"
        let testPassword = "TestPass123"
        await register(email: testEmail, password: testPassword)
    }
    #endif

    // MARK: - Session Management

    private func checkExistingSession() {
        guard keychain.getAccessToken() != nil else {
            isAuthenticated = false
            return
        }

        Task {
            await refreshCurrentUser()
        }
    }

    func refreshCurrentUser() async {
        do {
            let user: User = try await apiClient.request(AuthEndpoint.me)
            self.currentUser = user
            self.isAuthenticated = true
        } catch {
            // Token invalid, clear session
            signOut()
        }
    }

    // MARK: - Email/Password Auth

    func signIn(email: String, password: String) async {
        isLoading = true
        error = nil

        do {
            let response: AuthResponse = try await apiClient.request(
                AuthEndpoint.login(email: email, password: password)
            )

            keychain.saveAccessToken(response.accessToken)
            keychain.saveUserId(response.user.id)
            currentUser = response.user
            isAuthenticated = true
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func register(email: String, password: String) async {
        isLoading = true
        error = nil

        do {
            let response: AuthResponse = try await apiClient.request(
                AuthEndpoint.register(email: email, password: password)
            )

            keychain.saveAccessToken(response.accessToken)
            keychain.saveUserId(response.user.id)
            currentUser = response.user
            isAuthenticated = true
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Apple Sign-In

    func handleAppleSignIn(result: Result<ASAuthorization, Error>) async {
        isLoading = true
        error = nil

        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                  let identityToken = credential.identityToken,
                  let tokenString = String(data: identityToken, encoding: .utf8),
                  let authCodeData = credential.authorizationCode,
                  let authCode = String(data: authCodeData, encoding: .utf8) else {
                error = "Failed to get Apple credentials"
                isLoading = false
                return
            }

            // Get full name if provided (only on first sign-in)
            var fullName: String?
            if let nameComponents = credential.fullName {
                let formatter = PersonNameComponentsFormatter()
                let name = formatter.string(from: nameComponents)
                if !name.isEmpty {
                    fullName = name
                }
            }

            do {
                let response: AuthResponse = try await apiClient.request(
                    AuthEndpoint.appleSignIn(
                        identityToken: tokenString,
                        authorizationCode: authCode,
                        fullName: fullName
                    )
                )

                keychain.saveAccessToken(response.accessToken)
                keychain.saveUserId(response.user.id)
                currentUser = response.user
                isAuthenticated = true
            } catch let apiError as APIError {
                error = apiError.localizedDescription
            } catch {
                self.error = error.localizedDescription
            }

        case .failure(let authError):
            // Don't show error for user cancellation
            if (authError as? ASAuthorizationError)?.code != .canceled {
                error = authError.localizedDescription
            }
        }

        isLoading = false
    }

    // MARK: - Sign Out

    func signOut() {
        keychain.clearTokens()
        currentUser = nil
        isAuthenticated = false
        error = nil
    }
}
