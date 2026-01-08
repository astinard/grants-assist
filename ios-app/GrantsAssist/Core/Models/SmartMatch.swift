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

    enum CodingKeys: String, CodingKey {
        case ein, name, city, state
        case is501c3 = "is_501c3"
        case nteeCode = "ntee_code"
        case totalRevenue = "total_revenue"
        case totalAssets = "total_assets"
    }
}

/// Demographics from ZIP lookup
struct DemographicsResult: Codable {
    let locationName: String?
    let population: Int?
    let medianIncome: Double?
    let povertyRate: Double?
    let isHighNeed: Bool
    let incomeVsNational: Double?

    enum CodingKeys: String, CodingKey {
        case locationName = "location_name"
        case population
        case medianIncome = "median_income"
        case povertyRate = "poverty_rate"
        case isHighNeed = "is_high_need"
        case incomeVsNational = "income_vs_national"
    }
}

/// Rural status from ZIP lookup
struct RuralStatusResult: Codable {
    let isRural: Bool
    let ruccCode: Int?
    let description: String?
    let qualifiesUsda: Bool
    let qualifiesHrsa: Bool

    enum CodingKeys: String, CodingKey {
        case isRural = "is_rural"
        case ruccCode = "rucc_code"
        case description
        case qualifiesUsda = "qualifies_usda"
        case qualifiesHrsa = "qualifies_hrsa"
    }
}

/// ZIP lookup response
struct ZipLookupResponse: Codable {
    let zipCode: String
    let confidenceScore: Double
    let dataSources: [String]
    let demographics: DemographicsResult?
    let ruralStatus: RuralStatusResult?

    enum CodingKeys: String, CodingKey {
        case zipCode = "zip_code"
        case confidenceScore = "confidence_score"
        case dataSources = "data_sources"
        case demographics
        case ruralStatus = "rural_status"
    }
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

    enum CodingKeys: String, CodingKey {
        case programId = "program_id"
        case programName = "program_name"
        case agency, category
        case matchScore = "match_score"
        case eligibilityScore = "eligibility_score"
        case fitScore = "fit_score"
        case matchLevel = "match_level"
        case eligible
        case reasons
        case missingRequirements = "missing_requirements"
        case recommendations
        case maxAward = "max_award"
        case deadline
        case programUrl = "program_url"
    }

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

    enum CodingKeys: String, CodingKey {
        case ein, name
        case is501c3 = "is_501c3"
        case totalRevenue = "total_revenue"
    }
}

struct DemographicsAutoData: Codable {
    let povertyRate: Double?
    let medianIncome: Double?
    let isHighNeed: Bool?

    enum CodingKeys: String, CodingKey {
        case povertyRate = "poverty_rate"
        case medianIncome = "median_income"
        case isHighNeed = "is_high_need"
    }
}

struct RuralAutoData: Codable {
    let isRural: Bool?
    let qualifiesUsda: Bool?

    enum CodingKeys: String, CodingKey {
        case isRural = "is_rural"
        case qualifiesUsda = "qualifies_usda"
    }
}

/// Smart match response
struct SmartMatchResponse: Codable {
    let profileConfidence: Double
    let totalMatches: Int
    let matches: [SmartMatchResult]
    let autoDetected: AutoDetectedData?

    enum CodingKeys: String, CodingKey {
        case profileConfidence = "profile_confidence"
        case totalMatches = "total_matches"
        case matches
        case autoDetected = "auto_detected"
    }
}

/// Onboarding question
struct OnboardingQuestion: Codable, Identifiable {
    let id: String
    let question: String
    let type: String
    let options: [String]?
    let required: Bool
    let helpText: String?

    enum CodingKeys: String, CodingKey {
        case id, question, type, options, required
        case helpText = "help_text"
    }
}

/// Onboarding response
struct OnboardingResponse: Codable {
    let questions: [OnboardingQuestion]
    let estimatedMatches: Int

    enum CodingKeys: String, CodingKey {
        case questions
        case estimatedMatches = "estimated_matches"
    }
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

    enum CodingKeys: String, CodingKey {
        case orgName = "org_name"
        case orgType = "org_type"
        case ein
        case is501c3 = "is_501c3"
        case zipCode = "zip_code"
        case state
        case samRegistered = "sam_registered"
        case ueiNumber = "uei_number"
        case sector
        case minFunding = "min_funding"
        case maxFunding = "max_funding"
    }
}
