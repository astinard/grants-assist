import Foundation

// MARK: - Eligibility Result
struct EligibilityResult: Codable, Identifiable, Equatable {
    let programId: String
    let programName: String
    let matchScore: Int
    let eligible: Bool
    let missingRequirements: [String]
    let recommendations: [String]?

    var id: String { programId }

    var matchScoreText: String {
        "\(matchScore)%"
    }

    var matchLevel: MatchLevel {
        switch matchScore {
        case 80...100: return .excellent
        case 60..<80: return .good
        case 40..<60: return .fair
        default: return .poor
        }
    }

    enum MatchLevel {
        case excellent
        case good
        case fair
        case poor

        var displayName: String {
            switch self {
            case .excellent: return "Excellent Match"
            case .good: return "Good Match"
            case .fair: return "Fair Match"
            case .poor: return "Low Match"
            }
        }

        var color: String {
            switch self {
            case .excellent: return "green"
            case .good: return "blue"
            case .fair: return "orange"
            case .poor: return "red"
            }
        }

        var icon: String {
            switch self {
            case .excellent: return "star.fill"
            case .good: return "hand.thumbsup.fill"
            case .fair: return "questionmark.circle"
            case .poor: return "exclamationmark.triangle"
            }
        }
    }
}

// MARK: - Eligibility Check Response
struct EligibilityCheckResponse: Codable {
    let results: [EligibilityResult]
    let profileCompleteness: Int

    var topMatches: [EligibilityResult] {
        results.filter { $0.matchScore >= 60 }.prefix(5).map { $0 }
    }

    var hasGoodMatches: Bool {
        results.contains { $0.matchScore >= 60 }
    }
}
