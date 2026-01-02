import SwiftUI

struct ProgramDetailView: View {
    @Environment(\.dismiss) var dismiss
    @EnvironmentObject var appState: AppState
    let program: GrantProgram
    let eligibility: EligibilityResult?

    @State private var isApplying = false
    @State private var showingApplicationCreated = false
    @State private var createdApplication: Application?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // Header
                    headerSection

                    Divider()

                    // Eligibility Section
                    if let eligibility = eligibility {
                        eligibilitySection(eligibility)
                        Divider()
                    }

                    // Award Details
                    awardSection

                    Divider()

                    // Description
                    if let description = program.description {
                        descriptionSection(description)
                        Divider()
                    }

                    // Eligibility Requirements
                    if let summary = program.eligibilitySummary {
                        requirementsSection(summary)
                        Divider()
                    }

                    // Required Fields
                    if let fields = program.requiredFields, !fields.isEmpty {
                        requiredFieldsSection(fields)
                        Divider()
                    }

                    // Links
                    linksSection

                    Spacer(minLength: 100)
                }
                .padding()
            }
            .navigationTitle("Grant Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .safeAreaInset(edge: .bottom) {
                applyButton
            }
            .alert("Application Created", isPresented: $showingApplicationCreated) {
                Button("View Application") {
                    dismiss()
                    if let application = createdApplication {
                        appState.navigateToApplication(application)
                    }
                }
                Button("Continue Browsing", role: .cancel) {
                    dismiss()
                }
            } message: {
                Text("Your application for \(program.name) has been created. You can continue filling it out from the Applications tab.")
            }
        }
    }

    // MARK: - Header

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Category Badge
            HStack {
                Image(systemName: program.category.icon)
                Text(program.category.displayName)
            }
            .font(.subheadline)
            .fontWeight(.medium)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.accentColor.opacity(0.15))
            .foregroundStyle(Color.accentColor)
            .cornerRadius(16)

            // Title
            Text(program.name)
                .font(.title2)
                .fontWeight(.bold)

            // Agency
            Text(program.agency)
                .font(.headline)
                .foregroundStyle(.secondary)

            // Deadline Warning
            if program.isDeadlineSoon {
                HStack(spacing: 6) {
                    Image(systemName: "exclamationmark.circle.fill")
                    Text("Deadline approaching: \(program.deadlineText)")
                }
                .font(.subheadline)
                .foregroundStyle(.orange)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.orange.opacity(0.1))
                .cornerRadius(8)
            }
        }
    }

    // MARK: - Eligibility

    private func eligibilitySection(_ result: EligibilityResult) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Your Eligibility")
                .font(.headline)

            // Score
            HStack(spacing: 16) {
                // Progress Circle
                ZStack {
                    Circle()
                        .stroke(Color(.systemGray5), lineWidth: 8)

                    Circle()
                        .trim(from: 0, to: CGFloat(result.matchScore) / 100)
                        .stroke(colorForMatchLevel(result.matchLevel), style: StrokeStyle(lineWidth: 8, lineCap: .round))
                        .rotationEffect(.degrees(-90))

                    VStack(spacing: 2) {
                        Text("\(result.matchScore)%")
                            .font(.title2)
                            .fontWeight(.bold)
                        Text("match")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(width: 80, height: 80)

                VStack(alignment: .leading, spacing: 4) {
                    Text(result.matchLevel.displayName)
                        .font(.headline)
                        .foregroundStyle(colorForMatchLevel(result.matchLevel))

                    if result.eligible {
                        Label("You appear to be eligible", systemImage: "checkmark.circle.fill")
                            .font(.subheadline)
                            .foregroundStyle(.green)
                    } else {
                        Label("Some requirements may not be met", systemImage: "exclamationmark.triangle")
                            .font(.subheadline)
                            .foregroundStyle(.orange)
                    }
                }
            }

            // Missing Requirements
            if !result.missingRequirements.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Missing Requirements")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    ForEach(result.missingRequirements, id: \.self) { requirement in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: "xmark.circle")
                                .foregroundStyle(.red)
                            Text(requirement)
                        }
                        .font(.subheadline)
                    }
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Award

    private var awardSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Award Details")
                .font(.headline)

            HStack(spacing: 24) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Award Range")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(program.awardRange)
                        .font(.title3)
                        .fontWeight(.semibold)
                }

                if let matchText = program.matchRequiredText {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Match Required")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(matchText)
                            .font(.title3)
                            .fontWeight(.semibold)
                    }
                }

                Spacer()
            }

            HStack {
                Image(systemName: "calendar")
                Text("Deadline: \(program.deadlineText)")
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
    }

    // MARK: - Description

    private func descriptionSection(_ text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("About This Program")
                .font(.headline)

            Text(text)
                .font(.body)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Requirements

    private func requirementsSection(_ summary: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Eligibility Requirements")
                .font(.headline)

            Text(summary)
                .font(.body)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Required Fields

    private func requiredFieldsSection(_ fields: [String]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Required Information")
                .font(.headline)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                ForEach(fields, id: \.self) { field in
                    HStack(spacing: 6) {
                        Image(systemName: "checkmark.square")
                            .foregroundStyle(.secondary)
                        Text(field.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.caption)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    // MARK: - Links

    private var linksSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Resources")
                .font(.headline)

            if let urlString = program.programUrl, let url = URL(string: urlString) {
                Link(destination: url) {
                    HStack {
                        Image(systemName: "link")
                        Text("Program Website")
                        Spacer()
                        Image(systemName: "arrow.up.right")
                    }
                    .font(.subheadline)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
            }

            if let urlString = program.applicationUrl, let url = URL(string: urlString) {
                Link(destination: url) {
                    HStack {
                        Image(systemName: "doc.text")
                        Text("Official Application")
                        Spacer()
                        Image(systemName: "arrow.up.right")
                    }
                    .font(.subheadline)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
            }
        }
    }

    // MARK: - Apply Button

    private var applyButton: some View {
        VStack {
            Button {
                createApplication()
            } label: {
                HStack {
                    if isApplying {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(systemName: "plus.circle.fill")
                        Text("Start Application")
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color.accentColor)
                .foregroundStyle(.white)
                .cornerRadius(12)
            }
            .disabled(isApplying)
            .padding()
        }
        .background(.ultraThinMaterial)
    }

    // MARK: - Actions

    private func createApplication() {
        isApplying = true

        Task {
            do {
                let application: Application = try await APIClient.shared.request(
                    ApplicationEndpoint.create(programId: program.id)
                )
                createdApplication = application
                showingApplicationCreated = true
            } catch {
                print("Failed to create application: \(error)")
            }
            isApplying = false
        }
    }

    private func colorForMatchLevel(_ level: EligibilityResult.MatchLevel) -> Color {
        switch level {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .poor: return .red
        }
    }
}

#Preview {
    ProgramDetailView(
        program: GrantProgram(
            id: "test",
            name: "Small Business Innovation Research",
            agency: "National Science Foundation",
            category: .smallBusiness,
            minAward: 50000,
            maxAward: 250000,
            matchRequired: nil,
            description: "Funding for small businesses to engage in research and development.",
            eligibilitySummary: "Must be a US small business with fewer than 500 employees.",
            requiredFields: ["organization_name", "ein", "employee_count"],
            deadline: ISO8601DateFormatter().string(from: Date().addingTimeInterval(86400 * 14)),
            rollingDeadline: false,
            programUrl: "https://example.com",
            applicationUrl: nil,
            isActive: true
        ),
        eligibility: EligibilityResult(
            programId: "test",
            programName: "Test",
            matchScore: 75,
            eligible: true,
            missingRequirements: ["SAM.gov registration"],
            recommendations: nil
        )
    )
}
