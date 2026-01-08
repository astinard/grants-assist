import Foundation
import SwiftUI

@MainActor
final class SmartOnboardingViewModel: ObservableObject {
    // MARK: - Navigation
    @Published var currentStep = 0

    // MARK: - Step 1: Organization
    @Published var orgName = ""
    @Published var isSearchingOrg = false
    @Published var foundNonprofit: NonprofitSearchResult?
    @Published var nonprofitSuggestions: [NonprofitSearchResult] = []

    // MARK: - Step 2: ZIP Code
    @Published var zipCode = ""
    @Published var isSearchingZip = false
    @Published var zipData: ZipLookupResponse?

    // MARK: - Step 3: Sector
    @Published var sector: Sector?

    // MARK: - Step 4: Funding
    @Published var fundingRange: FundingRange?

    // MARK: - Step 5: SAM
    @Published var samStatus: SAMStatus?

    // MARK: - Results
    @Published var isLoadingMatches = false
    @Published var matchResponse: SmartMatchResponse?
    @Published var matchError: String?

    private let service = SmartMatchService.shared
    private var searchTask: Task<Void, Never>?

    // MARK: - Computed Properties

    var canProceed: Bool {
        switch currentStep {
        case 0: return !orgName.isEmpty
        case 1: return zipCode.count == 5
        case 2: return sector != nil
        case 3: return fundingRange != nil
        case 4: return samStatus != nil
        default: return true
        }
    }

    // MARK: - Navigation

    func nextStep() {
        if currentStep < 5 {
            currentStep += 1
        }
    }

    func previousStep() {
        if currentStep > 0 {
            currentStep -= 1
        }
    }

    // MARK: - Organization Lookup

    func lookupOrganization() async {
        guard !orgName.isEmpty else { return }

        searchTask?.cancel()

        searchTask = Task {
            isSearchingOrg = true
            foundNonprofit = nil
            nonprofitSuggestions = []

            do {
                let results = try await service.lookupNonprofit(name: orgName)

                if Task.isCancelled { return }

                if let exact = results.first(where: { $0.name.lowercased() == orgName.lowercased() }) {
                    foundNonprofit = exact
                } else if results.count == 1 {
                    foundNonprofit = results.first
                } else {
                    nonprofitSuggestions = results
                }
            } catch {
                print("Nonprofit lookup error: \(error)")
            }

            isSearchingOrg = false
        }
    }

    func selectNonprofit(_ nonprofit: NonprofitSearchResult) {
        foundNonprofit = nonprofit
        orgName = nonprofit.name
        nonprofitSuggestions = []
    }

    // MARK: - ZIP Code Lookup

    func lookupZipCode() async {
        guard zipCode.count == 5 else { return }

        isSearchingZip = true
        zipData = nil

        do {
            zipData = try await service.lookupZip(zipCode: zipCode)
        } catch {
            print("ZIP lookup error: \(error)")
        }

        isSearchingZip = false
    }

    // MARK: - Find Matches

    func findMatches() async {
        isLoadingMatches = true
        matchResponse = nil
        matchError = nil

        let request = SmartMatchRequest(
            orgName: orgName.isEmpty ? nil : orgName,
            orgType: "nonprofit",
            ein: foundNonprofit?.ein,
            is501c3: foundNonprofit?.is501c3,
            zipCode: zipCode.isEmpty ? nil : zipCode,
            samRegistered: samStatus?.boolValue,
            sector: sector?.apiValue,
            minFunding: fundingRange?.minValue,
            maxFunding: fundingRange?.maxValue
        )

        do {
            matchResponse = try await service.findMatches(request: request)
        } catch {
            matchError = error.localizedDescription
        }

        isLoadingMatches = false
    }
}
