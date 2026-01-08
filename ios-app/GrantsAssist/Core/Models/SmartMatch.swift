import Foundation

// MARK: - Smart Match Models

/// Response from nonprofit lookup
struct NonprofitSearchResult: Codable, Identifiable {
    let ein: String
    let name: String
    let city: String?
    let state: String?
    let is501c3: Bool
    let nteeCode: String?
    let totalRevenue: Double?
    let totalAssets: Double?

    var id: String { ein }
}

/// Demographics from ZIP lookup
struct DemographicsResult: Codable {
    let locationName: String?
    let population: Int?
    let medianIncome: Double?
    let povertyRate: Double?
    let isHighNeed: Bool
    let incomeVsNational: Double?
}

/// Rural status from ZIP lookup
struct RuralStatusResult: Codable {
    let isRural: Bool
    let ruccCode: Int?
    let description: String?
    let qualifiesUsda: Bool
    let qualifiesHrsa: Bool
}

/// ZIP lookup response
struct ZipLookupResponse: Codable {
    let zipCode: String
    let confidenceScore: Double
    let dataSources: [String]
    let demographics: DemographicsResult?
    let ruralStatus: RuralStatusResult?
}

/// Reason for a match score
struct MatchReason: Codable {
    let factor: String
    let points: Int
    let explanation: String
}

/// A single grant match from smart matching
struct SmartMatchResult: Codable, Identifiable {
    let programId: String
    let programName: String
    let agency: String
    let category: String
    let matchScore: Int
    let eligibilityScore: Int
    let fitScore: Int
    let matchLevel: String
    let eligible: Bool
    let reasons: [MatchReason]
    let missingRequirements: [String]
    let recommendations: [String]
    let maxAward: Double?
    let deadline: String?
    let programUrl: String?

    var id: String { programId }

    var awardText: String {
        if let award = maxAward {
            return "Up to $\(Int(award).formatted())"
        }
        return "Varies"
    }

    var deadlineText: String {
        deadline ?? "Rolling"
    }

    var matchLevelEnum: MatchLevel {
        switch matchLevel {
        case "excellent": return .excellent
        case "good": return .good
        case "fair": return .fair
        default: return .poor
        }
    }

    enum MatchLevel {
        case excellent, good, fair, poor

        var color: String {
            switch self {
            case .excellent: return "green"
            case .good: return "blue"
            case .fair: return "orange"
            case .poor: return "red"
            }
        }

        var medal: String {
            switch self {
            case .excellent: return "medal.fill"
            case .good: return "hand.thumbsup.fill"
            case .fair: return "questionmark.circle.fill"
            case .poor: return "exclamationmark.triangle.fill"
            }
        }
    }
}

/// Auto-detected data from smart matching
struct AutoDetectedData: Codable {
    let nonprofit: NonprofitAutoData?
    let demographics: DemographicsAutoData?
    let rural: RuralAutoData?
}

struct NonprofitAutoData: Codable {
    let ein: String?
    let name: String?
    let is501c3: Bool?
    let totalRevenue: Double?
}

struct DemographicsAutoData: Codable {
    let povertyRate: Double?
    let medianIncome: Double?
    let isHighNeed: Bool?
}

struct RuralAutoData: Codable {
    let isRural: Bool?
    let qualifiesUsda: Bool?
}

/// Smart match response
struct SmartMatchResponse: Codable {
    let profileConfidence: Double
    let totalMatches: Int
    let matches: [SmartMatchResult]
    let autoDetected: AutoDetectedData?
}

/// Onboarding question
struct OnboardingQuestion: Codable, Identifiable {
    let id: String
    let question: String
    let type: String
    let options: [String]?
    let required: Bool
    let helpText: String?
}

/// Onboarding response
struct OnboardingResponse: Codable {
    let questions: [OnboardingQuestion]
    let estimatedMatches: Int
}

// MARK: - Smart Match Request

struct SmartMatchRequest: Codable {
    var orgName: String?
    var orgType: String?
    var ein: String?
    var is501c3: Bool?
    var zipCode: String?
    var state: String?
    var samRegistered: Bool?
    var ueiNumber: String?
    var sector: String?
    var minFunding: Double?
    var maxFunding: Double?
}
