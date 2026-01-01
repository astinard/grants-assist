import SwiftUI

struct EligibilityView: View {
    @StateObject private var viewModel = EligibilityViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Profile Completeness Card
                    profileCompletenessCard

                    // Top Matches
                    if !viewModel.topMatches.isEmpty {
                        topMatchesSection
                    }

                    // All Results
                    if !viewModel.results.isEmpty {
                        allResultsSection
                    }
                }
                .padding()
            }
            .navigationTitle("Eligibility")
            .refreshable {
                await viewModel.checkEligibility()
            }
            .task {
                if viewModel.results.isEmpty {
                    await viewModel.checkEligibility()
                }
            }
            .overlay {
                if viewModel.isLoading {
                    ProgressView("Checking eligibility...")
                        .padding()
                        .background(.ultraThinMaterial)
                        .cornerRadius(12)
                }
            }
        }
    }

    // MARK: - Profile Completeness

    private var profileCompletenessCard: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Profile Completeness")
                        .font(.headline)

                    Text("A complete profile improves matching accuracy")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                ZStack {
                    Circle()
                        .stroke(Color(.systemGray5), lineWidth: 8)

                    Circle()
                        .trim(from: 0, to: CGFloat(viewModel.profileCompleteness) / 100)
                        .stroke(completenessColor, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                        .rotationEffect(.degrees(-90))

                    Text("\(viewModel.profileCompleteness)%")
                        .font(.headline)
                }
                .frame(width: 60, height: 60)
            }

            if viewModel.profileCompleteness < 80 {
                NavigationLink {
                    ProfileView()
                } label: {
                    HStack {
                        Image(systemName: "person.badge.plus")
                        Text("Complete Your Profile")
                    }
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
        .shadow(color: .black.opacity(0.05), radius: 8)
    }

    // MARK: - Top Matches

    private var topMatchesSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Top Matches")
                .font(.headline)

            ForEach(viewModel.topMatches) { result in
                EligibilityResultCard(result: result)
            }
        }
    }

    // MARK: - All Results

    private var allResultsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("All Programs")
                .font(.headline)

            ForEach(viewModel.results) { result in
                EligibilityResultRow(result: result)
            }
        }
    }

    private var completenessColor: Color {
        switch viewModel.profileCompleteness {
        case 80...100: return .green
        case 50..<80: return .orange
        default: return .red
        }
    }
}

// MARK: - Eligibility Result Card

struct EligibilityResultCard: View {
    let result: EligibilityResult

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(result.programName)
                        .font(.headline)

                    Text(result.matchLevel.displayName)
                        .font(.subheadline)
                        .foregroundStyle(matchColor)
                }

                Spacer()

                // Match Score Circle
                ZStack {
                    Circle()
                        .stroke(Color(.systemGray5), lineWidth: 6)

                    Circle()
                        .trim(from: 0, to: CGFloat(result.matchScore) / 100)
                        .stroke(matchColor, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                        .rotationEffect(.degrees(-90))

                    Text("\(result.matchScore)%")
                        .font(.caption)
                        .fontWeight(.bold)
                }
                .frame(width: 50, height: 50)
            }

            if !result.missingRequirements.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Missing:")
                        .font(.caption)
                        .fontWeight(.medium)

                    Text(result.missingRequirements.joined(separator: ", "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4)
    }

    private var matchColor: Color {
        switch result.matchLevel {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .poor: return .red
        }
    }
}

// MARK: - Eligibility Result Row

struct EligibilityResultRow: View {
    let result: EligibilityResult

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(result.programName)
                    .font(.subheadline)

                HStack(spacing: 4) {
                    Image(systemName: result.matchLevel.icon)
                    Text(result.matchLevel.displayName)
                }
                .font(.caption)
                .foregroundStyle(matchColor)
            }

            Spacer()

            Text("\(result.matchScore)%")
                .font(.headline)
                .foregroundStyle(matchColor)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    private var matchColor: Color {
        switch result.matchLevel {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .poor: return .red
        }
    }
}

// MARK: - ViewModel

@MainActor
final class EligibilityViewModel: ObservableObject {
    @Published var results: [EligibilityResult] = []
    @Published var profileCompleteness = 0
    @Published var isLoading = false
    @Published var error: String?

    private let apiClient = APIClient.shared

    var topMatches: [EligibilityResult] {
        results.filter { $0.matchScore >= 60 }.prefix(3).map { $0 }
    }

    func checkEligibility() async {
        isLoading = true
        error = nil

        do {
            let response: EligibilityCheckResponse = try await apiClient.request(
                EligibilityEndpoint.checkAll
            )

            results = response.results.sorted { $0.matchScore > $1.matchScore }
            profileCompleteness = response.profileCompleteness
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }
}

#Preview {
    EligibilityView()
}
