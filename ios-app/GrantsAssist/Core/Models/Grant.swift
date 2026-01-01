import Foundation

// MARK: - Grant Category
enum GrantCategory: String, Codable, CaseIterable, Identifiable {
    case healthcare = "healthcare"
    case smallBusiness = "small_business"
    case education = "education"
    case nonprofit = "nonprofit"
    case agriculture = "agriculture"
    case technology = "technology"
    case housing = "housing"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .healthcare: return "Healthcare"
        case .smallBusiness: return "Small Business"
        case .education: return "Education"
        case .nonprofit: return "Nonprofit"
        case .agriculture: return "Agriculture"
        case .technology: return "Technology"
        case .housing: return "Housing"
        }
    }

    var icon: String {
        switch self {
        case .healthcare: return "heart.circle.fill"
        case .smallBusiness: return "building.2.fill"
        case .education: return "graduationcap.fill"
        case .nonprofit: return "hands.sparkles.fill"
        case .agriculture: return "leaf.fill"
        case .technology: return "cpu.fill"
        case .housing: return "house.fill"
        }
    }

    var color: String {
        switch self {
        case .healthcare: return "red"
        case .smallBusiness: return "blue"
        case .education: return "purple"
        case .nonprofit: return "orange"
        case .agriculture: return "green"
        case .technology: return "cyan"
        case .housing: return "brown"
        }
    }
}

// MARK: - Grant Program
struct GrantProgram: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let agency: String
    let category: GrantCategory
    let minAward: Double?
    let maxAward: Double?
    let matchRequired: Double?
    let description: String?
    let eligibilitySummary: String?
    let requiredFields: [String]?
    let deadline: String?  // ISO8601 string from API
    let rollingDeadline: Bool?

    var deadlineDate: Date? {
        guard let deadline = deadline else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: deadline)
    }
    let programUrl: String?
    let applicationUrl: String?
    let isActive: Bool?

    var isRollingDeadline: Bool { rollingDeadline ?? false }
    var isActiveProgram: Bool { isActive ?? true }

    // MARK: - Computed Properties

    var awardRange: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0

        if let min = minAward, let max = maxAward {
            let minStr = formatter.string(from: NSNumber(value: min)) ?? "$\(Int(min))"
            let maxStr = formatter.string(from: NSNumber(value: max)) ?? "$\(Int(max))"
            return "\(minStr) - \(maxStr)"
        } else if let max = maxAward {
            let maxStr = formatter.string(from: NSNumber(value: max)) ?? "$\(Int(max))"
            return "Up to \(maxStr)"
        } else if let min = minAward {
            let minStr = formatter.string(from: NSNumber(value: min)) ?? "$\(Int(min))"
            return "Starting at \(minStr)"
        }
        return "Varies"
    }

    var deadlineText: String {
        if isRollingDeadline {
            return "Rolling"
        }
        guard let date = deadlineDate else {
            return "No deadline"
        }
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        return formatter.string(from: date)
    }

    var isDeadlineSoon: Bool {
        guard let date = deadlineDate, !isRollingDeadline else { return false }
        let daysUntilDeadline = Calendar.current.dateComponents([.day], from: Date(), to: date).day ?? 0
        return daysUntilDeadline <= 14 && daysUntilDeadline >= 0
    }

    var matchRequiredText: String? {
        guard let match = matchRequired, match > 0 else { return nil }
        return "\(Int(match))% match required"
    }
}

// MARK: - Programs Response
struct ProgramsResponse: Codable {
    let programs: [GrantProgram]
    let total: Int
}
