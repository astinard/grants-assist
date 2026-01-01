import SwiftUI

struct EmailAuthView: View {
    @EnvironmentObject var authService: AuthService
    @Environment(\.dismiss) var dismiss

    @State private var isSignUp = false
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""

    @FocusState private var focusedField: Field?

    enum Field {
        case email, password, confirmPassword
    }

    var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: true) {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Text(isSignUp ? "Create Account" : "Welcome Back")
                            .font(.title)
                            .fontWeight(.bold)

                        Text(isSignUp ? "Sign up to get started" : "Sign in to continue")
                            .foregroundStyle(.secondary)
                    }
                    .padding(.top, 24)

                    // Form Fields
                    VStack(spacing: 16) {
                        // Email
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Email")
                                .font(.subheadline)
                                .fontWeight(.medium)

                            TextField("you@example.com", text: $email)
                                .textContentType(.emailAddress)
                                .keyboardType(.emailAddress)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .focused($focusedField, equals: .email)
                                .padding()
                                .background(Color(.systemGray6))
                                .cornerRadius(12)
                        }

                        // Password
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Password")
                                .font(.subheadline)
                                .fontWeight(.medium)

                            SecureField("Enter your password", text: $password)
                                .textContentType(isSignUp ? .newPassword : .password)
                                .focused($focusedField, equals: .password)
                                .padding()
                                .background(Color(.systemGray6))
                                .cornerRadius(12)

                            // Password requirements hint
                            if isSignUp {
                                HStack(spacing: 4) {
                                    Image(systemName: password.count >= 8 ? "checkmark.circle.fill" : "circle")
                                        .foregroundStyle(password.count >= 8 ? .green : .secondary)
                                    Text("At least 8 characters")
                                        .foregroundStyle(password.count >= 8 ? .green : .secondary)
                                }
                                .font(.caption)
                            }
                        }

                        // Confirm Password (Sign Up only)
                        if isSignUp {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Confirm Password")
                                    .font(.subheadline)
                                    .fontWeight(.medium)

                                SecureField("Confirm your password", text: $confirmPassword)
                                    .textContentType(.newPassword)
                                    .focused($focusedField, equals: .confirmPassword)
                                    .padding()
                                    .background(passwordsMatch ? Color(.systemGray6) : Color.red.opacity(0.1))
                                    .cornerRadius(12)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12)
                                            .stroke(passwordsMatch ? Color.clear : Color.red.opacity(0.5), lineWidth: 1)
                                    )

                                // Match indicator
                                if !confirmPassword.isEmpty {
                                    HStack(spacing: 4) {
                                        Image(systemName: passwordsMatch ? "checkmark.circle.fill" : "xmark.circle.fill")
                                            .foregroundStyle(passwordsMatch ? .green : .red)
                                        Text(passwordsMatch ? "Passwords match" : "Passwords don't match")
                                            .foregroundStyle(passwordsMatch ? .green : .red)
                                    }
                                    .font(.caption)
                                }
                            }
                        }
                    }
                    .padding(.horizontal)

                    // Error Message
                    if let error = authService.error {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .padding(.horizontal)
                    }

                    // Submit Button
                    Button {
                        submitForm()
                    } label: {
                        Group {
                            if authService.isLoading {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text(isSignUp ? "Create Account" : "Sign In")
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(isFormValid ? Color.accentColor : Color.gray)
                        .foregroundStyle(.white)
                        .cornerRadius(12)
                    }
                    .disabled(!isFormValid || authService.isLoading)
                    .padding(.horizontal)

                    // Toggle Sign Up / Sign In
                    Button {
                        withAnimation {
                            isSignUp.toggle()
                            confirmPassword = ""
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Text(isSignUp ? "Already have an account?" : "Don't have an account?")
                                .foregroundStyle(.secondary)
                            Text(isSignUp ? "Sign In" : "Sign Up")
                                .fontWeight(.semibold)
                        }
                        .font(.subheadline)
                    }

                    Spacer()
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(leading: Button("Cancel") { dismiss() })
            .onChange(of: authService.isAuthenticated) { isAuthenticated in
                if isAuthenticated {
                    dismiss()
                }
            }
        }
    }

    private var passwordsMatch: Bool {
        confirmPassword.isEmpty || password == confirmPassword
    }

    private var isFormValid: Bool {
        let emailValid = email.contains("@") && email.contains(".")
        let passwordValid = password.count >= 8

        if isSignUp {
            return emailValid && passwordValid && password == confirmPassword && !confirmPassword.isEmpty
        }
        return emailValid && passwordValid
    }

    private func submitForm() {
        focusedField = nil

        Task {
            if isSignUp {
                await authService.register(email: email, password: password)
            } else {
                await authService.signIn(email: email, password: password)
            }
        }
    }
}

#Preview {
    EmailAuthView()
        .environmentObject(AuthService.shared)
}
