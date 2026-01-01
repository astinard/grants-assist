import SwiftUI

struct ProfileView: View {
    @StateObject private var viewModel = ProfileViewModel()

    var body: some View {
        NavigationStack {
            Form {
                // Completeness Section
                Section {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Profile Completeness")
                                .font(.headline)
                            Text("Complete your profile to improve eligibility matching")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        ZStack {
                            Circle()
                                .stroke(Color(.systemGray5), lineWidth: 6)
                                .frame(width: 50, height: 50)

                            Circle()
                                .trim(from: 0, to: CGFloat(viewModel.completenessScore) / 100)
                                .stroke(completenessColor, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                                .frame(width: 50, height: 50)
                                .rotationEffect(.degrees(-90))

                            Text("\(viewModel.completenessScore)%")
                                .font(.caption)
                                .fontWeight(.bold)
                        }
                    }
                    .padding(.vertical, 8)
                }

                // Personal Info
                Section("Personal Information") {
                    TextField("Full Name", text: $viewModel.fullName)
                        .textContentType(.name)

                    TextField("Phone", text: $viewModel.phone)
                        .textContentType(.telephoneNumber)
                        .keyboardType(.phonePad)
                }

                // Organization Info
                Section("Organization") {
                    TextField("Organization Name", text: $viewModel.organizationName)
                        .textContentType(.organizationName)

                    Picker("Organization Type", selection: $viewModel.organizationType) {
                        Text("Select Type").tag("")
                        Text("Sole Proprietor").tag("sole_proprietor")
                        Text("LLC").tag("llc")
                        Text("Corporation").tag("corporation")
                        Text("Nonprofit").tag("nonprofit")
                        Text("Partnership").tag("partnership")
                        Text("Other").tag("other")
                    }

                    TextField("Website", text: $viewModel.website)
                        .textContentType(.URL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                }

                // Address
                Section("Address") {
                    TextField("Street Address", text: $viewModel.address)
                        .textContentType(.streetAddressLine1)

                    TextField("City", text: $viewModel.city)
                        .textContentType(.addressCity)

                    TextField("State", text: $viewModel.state)
                        .textContentType(.addressState)

                    TextField("ZIP Code", text: $viewModel.zipCode)
                        .textContentType(.postalCode)
                        .keyboardType(.numberPad)
                }

                // Federal IDs
                Section("Federal Identifiers") {
                    TextField("EIN (Tax ID)", text: $viewModel.ein)
                        .keyboardType(.numberPad)

                    TextField("UEI Number", text: $viewModel.ueiNumber)

                    Toggle("SAM.gov Registered", isOn: $viewModel.samRegistered)
                }

                // Business Details
                Section("Business Details") {
                    TextField("Annual Revenue", text: $viewModel.annualRevenue)
                        .keyboardType(.decimalPad)

                    TextField("Number of Employees", text: $viewModel.employeeCount)
                        .keyboardType(.numberPad)

                    TextField("Years in Operation", text: $viewModel.yearsInOperation)
                        .keyboardType(.numberPad)
                }

                // Demographics
                Section("Demographics (Optional)") {
                    Toggle("Veteran-Owned", isOn: $viewModel.isVeteran)
                    Toggle("Minority-Owned", isOn: $viewModel.isMinorityOwned)
                    Toggle("Woman-Owned", isOn: $viewModel.isWomanOwned)
                    Toggle("Rural Location", isOn: $viewModel.isRural)
                }
            }
            .navigationTitle("Profile")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    if viewModel.hasUnsavedChanges {
                        Button("Save") {
                            Task { await viewModel.save() }
                        }
                        .disabled(viewModel.isSaving)
                    }
                }
            }
            .overlay {
                if viewModel.isSaving {
                    ProgressView()
                        .padding()
                        .background(.ultraThinMaterial)
                        .cornerRadius(12)
                }
            }
            .task {
                await viewModel.loadProfile()
            }
            .alert("Error", isPresented: .constant(viewModel.error != nil)) {
                Button("OK") { viewModel.error = nil }
            } message: {
                Text(viewModel.error ?? "")
            }
        }
    }

    private var completenessColor: Color {
        switch viewModel.completenessScore {
        case 80...100: return .green
        case 50..<80: return .orange
        default: return .red
        }
    }
}

// MARK: - ViewModel

@MainActor
final class ProfileViewModel: ObservableObject {
    @Published var fullName = ""
    @Published var phone = ""
    @Published var organizationName = ""
    @Published var organizationType = ""
    @Published var website = ""
    @Published var address = ""
    @Published var city = ""
    @Published var state = ""
    @Published var zipCode = ""
    @Published var ein = ""
    @Published var ueiNumber = ""
    @Published var samRegistered = false
    @Published var annualRevenue = ""
    @Published var employeeCount = ""
    @Published var yearsInOperation = ""
    @Published var isVeteran = false
    @Published var isMinorityOwned = false
    @Published var isWomanOwned = false
    @Published var isRural = false

    @Published var isLoading = false
    @Published var isSaving = false
    @Published var error: String?

    private var originalProfile: UserProfile?
    private let apiClient = APIClient.shared

    var completenessScore: Int {
        let fields: [String] = [fullName, phone, organizationName, organizationType,
                                address, city, state, zipCode, ein, ueiNumber]
        let filled = fields.filter { !$0.isEmpty }.count
        return Int((Double(filled) / Double(fields.count)) * 100)
    }

    var hasUnsavedChanges: Bool {
        guard let original = originalProfile else { return false }
        return fullName != (original.fullName ?? "") ||
               organizationName != (original.organizationName ?? "") ||
               phone != (original.phone ?? "")
        // Add more comparisons as needed
    }

    func loadProfile() async {
        isLoading = true

        do {
            let profile: UserProfile = try await apiClient.request(UserEndpoint.getProfile)
            populateFields(from: profile)
            originalProfile = profile
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func save() async {
        isSaving = true

        let profile = UserProfile(
            id: nil, fullName: fullName.isEmpty ? nil : fullName,
            organizationName: organizationName.isEmpty ? nil : organizationName,
            organizationType: organizationType.isEmpty ? nil : organizationType,
            address: address.isEmpty ? nil : address, city: city.isEmpty ? nil : city,
            state: state.isEmpty ? nil : state, zipCode: zipCode.isEmpty ? nil : zipCode,
            congressionalDistrict: nil, ein: ein.isEmpty ? nil : ein,
            ueiNumber: ueiNumber.isEmpty ? nil : ueiNumber, samRegistered: samRegistered,
            dunsNumber: nil, phone: phone.isEmpty ? nil : phone,
            website: website.isEmpty ? nil : website, isVeteran: isVeteran,
            isMinorityOwned: isMinorityOwned, isWomanOwned: isWomanOwned, isRural: isRural,
            annualRevenue: Double(annualRevenue), employeeCount: Int(employeeCount),
            yearsInOperation: Int(yearsInOperation), updatedAt: nil
        )

        do {
            let updated: UserProfile = try await apiClient.request(
                UserEndpoint.updateProfile(profile)
            )
            originalProfile = updated
        } catch {
            self.error = error.localizedDescription
        }

        isSaving = false
    }

    private func populateFields(from profile: UserProfile) {
        fullName = profile.fullName ?? ""
        phone = profile.phone ?? ""
        organizationName = profile.organizationName ?? ""
        organizationType = profile.organizationType ?? ""
        website = profile.website ?? ""
        address = profile.address ?? ""
        city = profile.city ?? ""
        state = profile.state ?? ""
        zipCode = profile.zipCode ?? ""
        ein = profile.ein ?? ""
        ueiNumber = profile.ueiNumber ?? ""
        samRegistered = profile.samRegistered ?? false
        annualRevenue = profile.annualRevenue.map { String(Int($0)) } ?? ""
        employeeCount = profile.employeeCount.map { String($0) } ?? ""
        yearsInOperation = profile.yearsInOperation.map { String($0) } ?? ""
        isVeteran = profile.isVeteran ?? false
        isMinorityOwned = profile.isMinorityOwned ?? false
        isWomanOwned = profile.isWomanOwned ?? false
        isRural = profile.isRural ?? false
    }
}

#Preview {
    ProfileView()
        .environmentObject(AuthService.shared)
}
