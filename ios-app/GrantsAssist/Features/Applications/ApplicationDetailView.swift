import SwiftUI

struct ApplicationDetailView: View {
    @Environment(\.dismiss) var dismiss
    @StateObject private var viewModel: ApplicationDetailViewModel

    init(application: Application) {
        _viewModel = StateObject(wrappedValue: ApplicationDetailViewModel(application: application))
    }

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView("Loading application...")
                } else {
                    ScrollView {
                        VStack(spacing: 24) {
                            // Status Header
                            statusHeader

                            // Progress Section
                            progressSection

                            Divider()

                            // Form Fields
                            formSection

                            // AI Narratives Section
                            if viewModel.application.status.isEditable {
                                narrativesSection
                            }

                            // Actions
                            if viewModel.application.status.isEditable {
                                actionsSection
                            }

                            Spacer(minLength: 100)
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Application")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }

                if viewModel.hasUnsavedChanges {
                    ToolbarItem(placement: .primaryAction) {
                        Button("Save") {
                            Task { await viewModel.save() }
                        }
                        .disabled(viewModel.isSaving)
                    }
                }
            }
            .alert("Error", isPresented: .constant(viewModel.error != nil)) {
                Button("OK") { viewModel.error = nil }
            } message: {
                Text(viewModel.error ?? "")
            }
        }
    }

    // MARK: - Status Header

    private var statusHeader: some View {
        VStack(spacing: 16) {
            // Program Info
            VStack(spacing: 4) {
                Text(viewModel.application.programName)
                    .font(.title3)
                    .fontWeight(.semibold)
                    .multilineTextAlignment(.center)
            }

            // Status Badge
            StatusBadge(status: viewModel.application.status)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }

    // MARK: - Progress

    private var progressSection: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Application Progress")
                    .font(.headline)
                Spacer()
                Text("\(Int(viewModel.application.completenessScore))%")
                    .font(.headline)
                    .foregroundStyle(progressColor)
            }

            // Progress Ring
            ZStack {
                Circle()
                    .stroke(Color(.systemGray5), lineWidth: 12)

                Circle()
                    .trim(from: 0, to: CGFloat(viewModel.application.completenessScore) / 100)
                    .stroke(progressColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeInOut, value: viewModel.application.completenessScore)

                VStack {
                    Text("\(Int(viewModel.application.completenessScore))%")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Complete")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 150, height: 150)
            .padding()
        }
    }

    // MARK: - Form

    private var formSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Application Details")
                .font(.headline)

            // Default application fields
            FormField(label: "Organization Name", value: $viewModel.organizationName, isRequired: true)
            FormField(label: "Project Title", value: $viewModel.projectTitle, isRequired: true)
            FormField(label: "Project Description", value: $viewModel.projectDescription, isRequired: true, isMultiline: true)
            FormField(label: "Requested Amount", value: $viewModel.requestedAmount, isRequired: true)
        }
    }

    // MARK: - Narratives

    private var narrativesSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("AI Writing Assistant")
                    .font(.headline)
                Spacer()
            }

            Text("Generate professional narratives for your grant application using AI.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Button {
                Task { await viewModel.generateNarratives() }
            } label: {
                HStack {
                    if viewModel.isGeneratingNarratives {
                        ProgressView()
                            .tint(.white)
                        Text("Generating...")
                    } else {
                        Image(systemName: "sparkles")
                        Text("Generate Narratives")
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .background(Color.purple)
                .foregroundStyle(.white)
                .cornerRadius(12)
            }
            .disabled(viewModel.isGeneratingNarratives)

            // Show generated narratives
            if !viewModel.narratives.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(Array(viewModel.narratives.keys.sorted()), id: \.self) { key in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(key.replacingOccurrences(of: "_", with: " ").capitalized)
                                .font(.subheadline)
                                .fontWeight(.medium)

                            Text(viewModel.narratives[key] ?? "")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(3)
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                }
            }
        }
    }

    // MARK: - Actions

    private var actionsSection: some View {
        VStack(spacing: 12) {
            if viewModel.application.completenessScore >= 80 {
                Button {
                    Task { await viewModel.submit() }
                } label: {
                    HStack {
                        if viewModel.isSubmitting {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Image(systemName: "paperplane.fill")
                            Text("Submit Application")
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(Color.green)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
                }
                .disabled(viewModel.isSubmitting)
            }

            Button {
                Task { await viewModel.save() }
            } label: {
                HStack {
                    if viewModel.isSaving {
                        ProgressView()
                    } else {
                        Image(systemName: "square.and.arrow.down")
                        Text("Save Draft")
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color(.systemGray5))
                .foregroundStyle(.primary)
                .cornerRadius(12)
            }
            .disabled(viewModel.isSaving)
        }
        .padding(.top)
    }

    private var progressColor: Color {
        switch viewModel.application.completenessScore {
        case 80...100: return .green
        case 50..<80: return .orange
        default: return .red
        }
    }
}

// MARK: - Form Field

struct FormField: View {
    let label: String
    @Binding var value: String
    var isRequired: Bool = false
    var isMultiline: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 4) {
                Text(label)
                    .font(.subheadline)
                    .fontWeight(.medium)

                if isRequired {
                    Text("*")
                        .foregroundStyle(.red)
                }
            }

            if isMultiline {
                TextEditor(text: $value)
                    .frame(minHeight: 100)
                    .padding(8)
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
            } else {
                TextField(label, text: $value)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
            }
        }
    }
}

// MARK: - ViewModel

@MainActor
final class ApplicationDetailViewModel: ObservableObject {
    @Published var application: Application
    @Published var formData: [String: String] = [:]
    @Published var narratives: [String: String] = [:]
    @Published var isLoading = false
    @Published var isSaving = false
    @Published var isSubmitting = false
    @Published var isGeneratingNarratives = false
    @Published var error: String?

    // Common form fields
    @Published var organizationName = ""
    @Published var projectTitle = ""
    @Published var projectDescription = ""
    @Published var requestedAmount = ""

    private let apiClient = APIClient.shared
    private var originalFormData: [String: String] = [:]

    var hasUnsavedChanges: Bool {
        formData != originalFormData
    }

    init(application: Application) {
        self.application = application
        Task { await loadFormData() }
    }

    func loadFormData() async {
        isLoading = true

        do {
            let response: FormDataResponse = try await apiClient.request(
                ApplicationEndpoint.formData(applicationId: application.id)
            )

            // Extract string values from form data
            for (key, value) in response.formData {
                if let stringValue = value.value as? String {
                    formData[key] = stringValue
                }
            }

            // Extract narratives if present
            if let narrativesData = response.formData["narratives"]?.value as? [String: Any] {
                for (key, value) in narrativesData {
                    if let text = value as? String {
                        narratives[key] = text
                    }
                }
            }

            // Populate common fields
            organizationName = formData["organization_name"] ?? ""
            projectTitle = formData["project_title"] ?? ""
            projectDescription = formData["project_description"] ?? ""
            requestedAmount = formData["requested_amount"] ?? ""

            originalFormData = formData
        } catch {
            print("Failed to load form data: \(error)")
        }

        isLoading = false
    }

    func binding(for field: String) -> Binding<String> {
        Binding(
            get: { self.formData[field] ?? "" },
            set: { self.formData[field] = $0 }
        )
    }

    func generateNarratives() async {
        isGeneratingNarratives = true
        error = nil

        do {
            let response: NarrativesResponse = try await apiClient.request(
                ApplicationEndpoint.generateNarratives(
                    applicationId: application.id,
                    projectSummary: projectDescription.isEmpty ? nil : projectDescription
                )
            )

            narratives = response.sections

            // Reload form data to get updated narratives
            await loadFormData()
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isGeneratingNarratives = false
    }

    func save() async {
        isSaving = true
        error = nil

        // Sync common fields
        formData["organization_name"] = organizationName
        formData["project_title"] = projectTitle
        formData["project_description"] = projectDescription
        formData["requested_amount"] = requestedAmount

        do {
            let codableFormData = formData.mapValues { AnyCodable($0) }
            let request = ApplicationUpdateRequest(status: .inProgress, formData: codableFormData)

            let updated: Application = try await apiClient.request(
                ApplicationEndpoint.update(applicationId: application.id, request: request)
            )

            application = updated
            originalFormData = formData
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isSaving = false
    }

    func submit() async {
        isSubmitting = true
        error = nil

        // Save first
        await save()

        do {
            let request = ApplicationUpdateRequest(status: .submitted, formData: nil)

            let updated: Application = try await apiClient.request(
                ApplicationEndpoint.update(applicationId: application.id, request: request)
            )

            application = updated
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isSubmitting = false
    }
}

#Preview {
    ApplicationDetailView(
        application: Application(
            id: "test",
            programId: "program",
            programName: "Test Grant Program",
            status: .inProgress,
            completenessScore: 65,
            createdAt: ISO8601DateFormatter().string(from: Date()),
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            submittedAt: nil
        )
    )
}
