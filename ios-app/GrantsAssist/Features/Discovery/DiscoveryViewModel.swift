import Foundation

@MainActor
final class DiscoveryViewModel: ObservableObject {
    @Published var programs: [GrantProgram] = []
    @Published var eligibilityResults: [String: EligibilityResult] = [:]
    @Published var selectedCategory: GrantCategory?
    @Published var searchText = ""
    @Published var isLoading = false
    @Published var isLoadingEligibility = false
    @Published var error: String?

    private let apiClient = APIClient.shared

    var filteredPrograms: [GrantProgram] {
        programs.sorted { lhs, rhs in
            // Sort by eligibility score if available
            let lhsScore = eligibilityResults[lhs.id]?.matchScore ?? 0
            let rhsScore = eligibilityResults[rhs.id]?.matchScore ?? 0
            return lhsScore > rhsScore
        }
    }

    var categories: [GrantCategory] {
        GrantCategory.allCases
    }

    // MARK: - Load Programs

    func loadPrograms() async {
        isLoading = true
        error = nil

        do {
            let response: ProgramsResponse = try await apiClient.request(
                ProgramEndpoint.list(
                    category: selectedCategory,
                    search: searchText.isEmpty ? nil : searchText,
                    activeOnly: true
                )
            )
            programs = response.programs
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Load Eligibility

    func loadEligibility() async {
        isLoadingEligibility = true

        do {
            let response: EligibilityCheckResponse = try await apiClient.request(
                EligibilityEndpoint.checkAll
            )

            eligibilityResults = Dictionary(
                uniqueKeysWithValues: response.results.map { ($0.programId, $0) }
            )
        } catch {
            // Silently fail - eligibility is optional enhancement
            print("Failed to load eligibility: \(error)")
        }

        isLoadingEligibility = false
    }

    // MARK: - Search

    func search() async {
        await loadPrograms()
    }

    // MARK: - Filter by Category

    func selectCategory(_ category: GrantCategory?) {
        selectedCategory = category
        Task {
            await loadPrograms()
        }
    }

    // MARK: - Refresh

    func refresh() async {
        await loadPrograms()
        await loadEligibility()
    }
}
