import Foundation

// MARK: - Application Status
enum ApplicationStatus: String, Codable, CaseIterable {
    case draft = "draft"
    case inProgress = "in_progress"
    case readyToSubmit = "ready_to_submit"
    case submitted = "submitted"
    case underReview = "under_review"
    case approved = "approved"
    case denied = "denied"

    var displayName: String {
        switch self {
        case .draft: return "Draft"
        case .inProgress: return "In Progress"
        case .readyToSubmit: return "Ready to Submit"
        case .submitted: return "Submitted"
        case .underReview: return "Under Review"
        case .approved: return "Approved"
        case .denied: return "Denied"
        }
    }

    var icon: String {
        switch self {
        case .draft: return "doc"
        case .inProgress: return "pencil.circle"
        case .readyToSubmit: return "checkmark.circle"
        case .submitted: return "paperplane.fill"
        case .underReview: return "clock"
        case .approved: return "checkmark.seal.fill"
        case .denied: return "xmark.circle.fill"
        }
    }

    var color: String {
        switch self {
        case .draft: return "gray"
        case .inProgress: return "blue"
        case .readyToSubmit: return "orange"
        case .submitted: return "purple"
        case .underReview: return "yellow"
        case .approved: return "green"
        case .denied: return "red"
        }
    }

    var isEditable: Bool {
        switch self {
        case .draft, .inProgress, .readyToSubmit:
            return true
        case .submitted, .underReview, .approved, .denied:
            return false
        }
    }

    var isFinal: Bool {
        self == .approved || self == .denied
    }
}

// MARK: - Application
struct Application: Codable, Identifiable, Equatable {
    let id: String
    let programId: String
    let programName: String
    let status: ApplicationStatus
    let completenessScore: Double
    let createdAt: String  // ISO8601 string
    let updatedAt: String  // ISO8601 string
    let submittedAt: String?

    var createdDate: Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: createdAt)
    }

    var updatedDate: Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: updatedAt)
    }

    var lastModifiedText: String {
        guard let date = updatedDate else { return "Unknown" }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    var submittedText: String? {
        guard let submitted = submittedAt else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: submitted) else { return nil }
        let dateFormatter = DateFormatter()
        dateFormatter.dateStyle = .medium
        return dateFormatter.string(from: date)
    }
}

// MARK: - Applications Response
struct ApplicationsResponse: Codable {
    let applications: [Application]
    let total: Int
}

// MARK: - Application Update Request
struct ApplicationUpdateRequest: Codable {
    var status: ApplicationStatus?
    var formData: [String: AnyCodable]?
}

// MARK: - Form Data Response
struct FormDataResponse: Codable {
    let applicationId: String
    let programId: String
    let programName: String
    let formData: [String: AnyCodable]
    let status: String
}

// MARK: - Narratives Response
struct NarrativesResponse: Codable {
    let sections: [String: String]
    let message: String
}

// MARK: - AnyCodable (for flexible JSON)
struct AnyCodable: Codable, Equatable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self.value = NSNull()
        } else if let bool = try? container.decode(Bool.self) {
            self.value = bool
        } else if let int = try? container.decode(Int.self) {
            self.value = int
        } else if let double = try? container.decode(Double.self) {
            self.value = double
        } else if let string = try? container.decode(String.self) {
            self.value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            self.value = array.map(\.value)
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            self.value = dict.mapValues(\.value)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unsupported type")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case is NSNull:
            try container.encodeNil()
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dict as [String: Any]:
            try container.encode(dict.mapValues { AnyCodable($0) })
        default:
            throw EncodingError.invalidValue(value, .init(codingPath: [], debugDescription: "Unsupported type"))
        }
    }

    static func == (lhs: AnyCodable, rhs: AnyCodable) -> Bool {
        String(describing: lhs.value) == String(describing: rhs.value)
    }
}
