import Foundation

// MARK: - AI Writer Models

struct SectionInfo: Codable, Identifiable {
    let type: String
    let title: String
    let description: String
    let minWords: Int
    let maxWords: Int
    let keyElements: [String]

    var id: String { type }
}

struct SectionsListResponse: Codable {
    let sections: [SectionInfo]
}

struct SectionStatus: Codable, Identifiable {
    let sectionType: String
    let title: String
    let hasContent: Bool
    let wordCount: Int
    let qualityScore: Double?
    let version: Int
    let isUserEdited: Bool

    var id: String { sectionType }
}

struct WritingStatusResponse: Codable {
    let applicationId: String
    let sections: [SectionStatus]
    let progress: Int
    let completedSections: Int
    let totalSections: Int
    let totalWords: Int
    let estimatedPages: Double
}

struct GenerateSectionRequest: Codable {
    let sectionType: String
    let additionalContext: String?
    let tone: String?
}

struct GenerateSectionResponse: Codable {
    let applicationId: String
    let sectionType: String
    let content: String
    let wordCount: Int
    let qualityScore: Double
    let qualityFeedback: String
    let suggestions: [String]
    let model: String
}

struct ImproveSectionRequest: Codable {
    let sectionType: String
    let currentContent: String
    let improvementFocus: String
}

struct SectionContentResponse: Codable {
    let applicationId: String
    let sectionType: String
    let title: String
    let content: String?
    let wordCount: Int
    let qualityScore: Double?
    let hasContent: Bool
    let version: Int?
    let isUserEdited: Bool?
    let keyElements: [String]
}

struct UpdateSectionRequest: Codable {
    let content: String
}

struct GenerateAllResponse: Codable {
    let applicationId: String
    let sectionsGenerated: Int
    let totalSections: Int
    let totalWords: Int
    let averageQuality: Double
    let estimatedPages: Double
}

// MARK: - Full Agent Application Models

struct GenerateFullApplicationRequest: Codable {
    let projectTitle: String
    let projectSummary: String
}

struct FullApplicationResponse: Codable {
    let applicationId: String
    let grantId: String
    let projectTitle: String
    let generationTimeSeconds: Double
    let wordCount: Int
    let sectionCount: Int
    let fullApplication: String
    let sections: [String]
    let message: String
}

// MARK: - AI Writer Endpoints

enum AIWriterEndpoint: APIEndpoint {
    case listSections
    case getWritingStatus(applicationId: String)
    case generateSection(applicationId: String, request: GenerateSectionRequest)
    case improveSection(applicationId: String, request: ImproveSectionRequest)
    case generateAll(applicationId: String, tone: String?)
    case getSectionContent(applicationId: String, sectionType: String)
    case updateSection(applicationId: String, sectionType: String, content: String)
    case generateFullAgent(applicationId: String, request: GenerateFullApplicationRequest)

    var path: String {
        switch self {
        case .listSections:
            return "/api/ai-writer/sections"
        case .getWritingStatus(let appId):
            return "/api/ai-writer/applications/\(appId)/status"
        case .generateSection(let appId, _):
            return "/api/ai-writer/applications/\(appId)/generate"
        case .improveSection(let appId, _):
            return "/api/ai-writer/applications/\(appId)/improve"
        case .generateAll(let appId, _):
            return "/api/ai-writer/applications/\(appId)/generate-all"
        case .getSectionContent(let appId, let sectionType):
            return "/api/ai-writer/applications/\(appId)/sections/\(sectionType)"
        case .updateSection(let appId, let sectionType, _):
            return "/api/ai-writer/applications/\(appId)/sections/\(sectionType)"
        case .generateFullAgent(let appId, _):
            return "/api/ai-writer/applications/\(appId)/generate-full-agent"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .listSections, .getWritingStatus, .getSectionContent:
            return .get
        case .generateSection, .improveSection, .generateAll, .generateFullAgent:
            return .post
        case .updateSection:
            return .put
        }
    }

    var queryItems: [URLQueryItem]? {
        switch self {
        case .generateAll(_, let tone):
            if let tone = tone {
                return [URLQueryItem(name: "tone", value: tone)]
            }
            return nil
        default:
            return nil
        }
    }

    var body: Data? {
        switch self {
        case .generateSection(_, let request):
            return try? JSONEncoder().encode(request)
        case .improveSection(_, let request):
            return try? JSONEncoder().encode(request)
        case .updateSection(_, _, let content):
            let request = UpdateSectionRequest(content: content)
            return try? JSONEncoder().encode(request)
        case .generateFullAgent(_, let request):
            return try? JSONEncoder().encode(request)
        default:
            return nil
        }
    }

    var requiresAuth: Bool { true }
}

// MARK: - AI Writer Service

@MainActor
final class AIWriterService: ObservableObject {
    static let shared = AIWriterService()

    private let apiClient = APIClient.shared

    @Published var isLoading = false
    @Published var error: String?
    @Published var availableSections: [SectionInfo] = []

    private init() {}

    // MARK: - Get Available Sections

    func loadAvailableSections() async {
        isLoading = true
        error = nil

        do {
            let response: SectionsListResponse = try await apiClient.request(AIWriterEndpoint.listSections)
            availableSections = response.sections
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Get Writing Status

    func getWritingStatus(applicationId: String) async throws -> WritingStatusResponse {
        return try await apiClient.request(AIWriterEndpoint.getWritingStatus(applicationId: applicationId))
    }

    // MARK: - Generate Section

    func generateSection(
        applicationId: String,
        sectionType: String,
        additionalContext: String? = nil,
        tone: String = "professional"
    ) async throws -> GenerateSectionResponse {
        let request = GenerateSectionRequest(
            sectionType: sectionType,
            additionalContext: additionalContext,
            tone: tone
        )

        return try await apiClient.request(
            AIWriterEndpoint.generateSection(applicationId: applicationId, request: request)
        )
    }

    // MARK: - Improve Section

    func improveSection(
        applicationId: String,
        sectionType: String,
        currentContent: String,
        improvementFocus: String
    ) async throws -> GenerateSectionResponse {
        let request = ImproveSectionRequest(
            sectionType: sectionType,
            currentContent: currentContent,
            improvementFocus: improvementFocus
        )

        return try await apiClient.request(
            AIWriterEndpoint.improveSection(applicationId: applicationId, request: request)
        )
    }

    // MARK: - Generate All Sections

    func generateAllSections(
        applicationId: String,
        tone: String = "professional"
    ) async throws -> GenerateAllResponse {
        return try await apiClient.request(
            AIWriterEndpoint.generateAll(applicationId: applicationId, tone: tone)
        )
    }

    // MARK: - Get Section Content

    func getSectionContent(
        applicationId: String,
        sectionType: String
    ) async throws -> SectionContentResponse {
        return try await apiClient.request(
            AIWriterEndpoint.getSectionContent(applicationId: applicationId, sectionType: sectionType)
        )
    }

    // MARK: - Update Section

    func updateSection(
        applicationId: String,
        sectionType: String,
        content: String
    ) async throws {
        try await apiClient.requestVoid(
            AIWriterEndpoint.updateSection(applicationId: applicationId, sectionType: sectionType, content: content)
        )
    }

    // MARK: - Generate Full Application with AI Agent

    /// Generate a complete grant application using the autonomous AI agent.
    /// This researches requirements, gathers data, and writes all sections.
    /// May take 30-60 seconds to complete.
    func generateFullApplication(
        applicationId: String,
        projectTitle: String,
        projectSummary: String
    ) async throws -> FullApplicationResponse {
        let request = GenerateFullApplicationRequest(
            projectTitle: projectTitle,
            projectSummary: projectSummary
        )

        return try await apiClient.request(
            AIWriterEndpoint.generateFullAgent(applicationId: applicationId, request: request)
        )
    }
}
