import SwiftUI

extension Color {
    // MARK: - Brand Colors
    static let brandPrimary = Color("AccentColor")
    static let brandSecondary = Color.blue

    // MARK: - Semantic Colors
    static let success = Color.green
    static let warning = Color.orange
    static let error = Color.red
    static let info = Color.blue

    // MARK: - Background Colors
    static let cardBackground = Color(.systemBackground)
    static let groupedBackground = Color(.systemGroupedBackground)

    // MARK: - Grant Categories
    static func categoryColor(for category: GrantCategory) -> Color {
        switch category {
        case .healthcare: return .red
        case .smallBusiness: return .blue
        case .education: return .purple
        case .nonprofit: return .orange
        case .agriculture: return .green
        case .technology: return .cyan
        case .housing: return .brown
        }
    }

    // MARK: - Match Levels
    static func matchColor(for score: Int) -> Color {
        switch score {
        case 80...100: return .green
        case 60..<80: return .blue
        case 40..<60: return .orange
        default: return .red
        }
    }
}
