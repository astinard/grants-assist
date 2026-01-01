import Foundation

// MARK: - User
struct User: Codable, Identifiable, Equatable {
    let id: String
    let email: String
    let subscriptionTier: SubscriptionTier
    let subscriptionExpiresAt: Date?
    let createdAt: Date?
    let lastLoginAt: Date?

    var isSubscribed: Bool {
        guard subscriptionTier != .free else { return false }
        guard let expiresAt = subscriptionExpiresAt else { return false }
        return expiresAt > Date()
    }
}

// MARK: - Subscription Tier
enum SubscriptionTier: String, Codable, CaseIterable {
    case free = "free"
    case pro = "pro"
    case business = "business"

    var displayName: String {
        switch self {
        case .free: return "Free"
        case .pro: return "Pro"
        case .business: return "Business"
        }
    }

    var applicationsPerMonth: Int {
        switch self {
        case .free: return Configuration.SubscriptionLimits.freeApplicationsPerMonth
        case .pro: return Configuration.SubscriptionLimits.proApplicationsPerMonth
        case .business: return Configuration.SubscriptionLimits.businessApplicationsPerMonth
        }
    }

    var price: String {
        switch self {
        case .free: return "Free"
        case .pro: return "$9.99/mo"
        case .business: return "$29.99/mo"
        }
    }
}

// MARK: - Auth Response
struct AuthResponse: Codable {
    let accessToken: String
    let tokenType: String
    let user: User
}

// MARK: - User Profile
struct UserProfile: Codable, Equatable {
    var id: String?
    var fullName: String?
    var organizationName: String?
    var organizationType: String?
    var address: String?
    var city: String?
    var state: String?
    var zipCode: String?
    var congressionalDistrict: String?
    var ein: String?
    var ueiNumber: String?
    var samRegistered: Bool?
    var dunsNumber: String?
    var phone: String?
    var website: String?
    var isVeteran: Bool?
    var isMinorityOwned: Bool?
    var isWomanOwned: Bool?
    var isRural: Bool?
    var annualRevenue: Double?
    var employeeCount: Int?
    var yearsInOperation: Int?
    var updatedAt: Date?

    // MARK: - Computed Properties

    var completenessScore: Int {
        let fields: [Any?] = [
            fullName, organizationName, organizationType,
            address, city, state, zipCode,
            phone, ein, ueiNumber
        ]
        let filledCount = fields.compactMap { $0 }.count
        return Int((Double(filledCount) / Double(fields.count)) * 100)
    }

    var hasBasicInfo: Bool {
        fullName != nil && !fullName!.isEmpty
    }

    var hasOrganizationInfo: Bool {
        organizationName != nil && !organizationName!.isEmpty
    }

    var hasFederalIds: Bool {
        (ein != nil && !ein!.isEmpty) || (ueiNumber != nil && !ueiNumber!.isEmpty)
    }
}

