import Foundation

// MARK: - Smart Match Endpoints

enum SmartMatchEndpoint: APIEndpoint {
    case lookupNonprofit(name: String, state: String?)
    case lookupZip(zipCode: String)
    case findMatches(request: SmartMatchRequest)
    case getOnboarding
    case getTop3(orgName: String, zipCode: String, sector: String)

    var path: String {
        switch self {
        case .lookupNonprofit:
            return "/api/smart-match/lookup/nonprofit"
        case .lookupZip:
            return "/api/smart-match/lookup/zip"
        case .findMatches:
            return "/api/smart-match/find"
        case .getOnboarding:
            return "/api/smart-match/onboarding"
        case .getTop3:
            return "/api/smart-match/top3"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .lookupNonprofit, .lookupZip, .getOnboarding, .getTop3:
            return .get
        case .findMatches:
            return .post
        }
    }

    var queryItems: [URLQueryItem]? {
        switch self {
        case .lookupNonprofit(let name, let state):
            var items = [URLQueryItem(name: "name", value: name)]
            if let state = state {
                items.append(URLQueryItem(name: "state", value: state))
            }
            return items

        case .lookupZip(let zipCode):
            return [URLQueryItem(name: "zip_code", value: zipCode)]

        case .getTop3(let orgName, let zipCode, let sector):
            return [
                URLQueryItem(name: "org_name", value: orgName),
                URLQueryItem(name: "zip_code", value: zipCode),
                URLQueryItem(name: "sector", value: sector)
            ]

        default:
            return nil
        }
    }

    var body: Data? {
        switch self {
        case .findMatches(let request):
            return try? JSONEncoder().encode(request)
        default:
            return nil
        }
    }

    var requiresAuth: Bool {
        // Smart match endpoints work without auth for onboarding
        return false
    }
}

// MARK: - Smart Match Service

@MainActor
final class SmartMatchService: ObservableObject {
    static let shared = SmartMatchService()

    private let apiClient = APIClient.shared

    @Published var isLoading = false
    @Published var error: String?

    private init() {}

    // MARK: - Nonprofit Lookup

    func lookupNonprofit(name: String, state: String? = nil) async throws -> [NonprofitSearchResult] {
        isLoading = true
        defer { isLoading = false }

        return try await apiClient.request(SmartMatchEndpoint.lookupNonprofit(name: name, state: state))
    }

    // MARK: - ZIP Lookup

    func lookupZip(zipCode: String) async throws -> ZipLookupResponse {
        isLoading = true
        defer { isLoading = false }

        return try await apiClient.request(SmartMatchEndpoint.lookupZip(zipCode: zipCode))
    }

    // MARK: - Find Matches

    func findMatches(request: SmartMatchRequest) async throws -> SmartMatchResponse {
        isLoading = true
        defer { isLoading = false }

        return try await apiClient.request(SmartMatchEndpoint.findMatches(request: request))
    }

    // MARK: - Get Top 3 Matches

    func getTop3(orgName: String, zipCode: String, sector: String) async throws -> SmartMatchResponse {
        isLoading = true
        defer { isLoading = false }

        return try await apiClient.request(SmartMatchEndpoint.getTop3(orgName: orgName, zipCode: zipCode, sector: sector))
    }

    // MARK: - Get Onboarding Questions

    func getOnboardingQuestions() async throws -> OnboardingResponse {
        return try await apiClient.request(SmartMatchEndpoint.getOnboarding)
    }
}
