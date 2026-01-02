import Foundation

// MARK: - Shared Encoder
private let sharedEncoder: JSONEncoder = {
    let encoder = JSONEncoder()
    encoder.keyEncodingStrategy = .convertToSnakeCase
    return encoder
}()

// MARK: - Auth Endpoints
enum AuthEndpoint: APIEndpoint {
    case register(email: String, password: String)
    case login(email: String, password: String)
    case appleSignIn(identityToken: String, authorizationCode: String, fullName: String?)
    case me

    var path: String {
        switch self {
        case .register: return "/api/auth/register"
        case .login: return "/api/auth/token"
        case .appleSignIn: return "/api/auth/apple"
        case .me: return "/api/auth/me"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .register, .login, .appleSignIn: return .post
        case .me: return .get
        }
    }

    var body: Data? {
        switch self {
        case .register(let email, let password):
            return try? sharedEncoder.encode([
                "email": email,
                "password": password
            ])
        case .login(let email, let password):
            // OAuth2 form data format
            let formData = "username=\(email)&password=\(password)"
            return formData.data(using: .utf8)
        case .appleSignIn(let token, let code, let name):
            var payload: [String: String] = [
                "identity_token": token,
                "authorization_code": code
            ]
            if let name = name {
                payload["full_name"] = name
            }
            return try? sharedEncoder.encode(payload)
        case .me:
            return nil
        }
    }

    var headers: [String: String]? {
        switch self {
        case .login:
            return ["Content-Type": "application/x-www-form-urlencoded"]
        default:
            return nil
        }
    }

    var requiresAuth: Bool {
        switch self {
        case .register, .login, .appleSignIn: return false
        case .me: return true
        }
    }
}

// MARK: - User Endpoints
enum UserEndpoint: APIEndpoint {
    case getProfile
    case updateProfile(UserProfile)

    var path: String {
        "/api/users/profile"
    }

    var method: HTTPMethod {
        switch self {
        case .getProfile: return .get
        case .updateProfile: return .patch
        }
    }

    var body: Data? {
        switch self {
        case .getProfile: return nil
        case .updateProfile(let request): return try? sharedEncoder.encode(request)
        }
    }
}

// MARK: - Program Endpoints
enum ProgramEndpoint: APIEndpoint {
    case list(category: GrantCategory?, search: String?, activeOnly: Bool)
    case categories
    case detail(programId: String)

    var path: String {
        switch self {
        case .list: return "/api/programs/"
        case .categories: return "/api/programs/categories/"
        case .detail(let id): return "/api/programs/\(id)"
        }
    }

    var method: HTTPMethod { .get }

    var queryItems: [URLQueryItem]? {
        switch self {
        case .list(let category, let search, let activeOnly):
            var items: [URLQueryItem] = []
            if let category = category {
                items.append(URLQueryItem(name: "category", value: category.rawValue))
            }
            if let search = search, !search.isEmpty {
                items.append(URLQueryItem(name: "search", value: search))
            }
            items.append(URLQueryItem(name: "active_only", value: String(activeOnly)))
            return items.isEmpty ? nil : items
        default:
            return nil
        }
    }
}

// MARK: - Application Endpoints
enum ApplicationEndpoint: APIEndpoint {
    case list(status: ApplicationStatus?)
    case create(programId: String)
    case detail(applicationId: String)
    case formData(applicationId: String)
    case update(applicationId: String, request: ApplicationUpdateRequest)
    case delete(applicationId: String)
    case generateNarratives(applicationId: String, projectSummary: String?)
    case downloadPDF(applicationId: String)

    var path: String {
        switch self {
        case .list: return "/api/applications/"
        case .create: return "/api/applications/"
        case .detail(let id): return "/api/applications/\(id)"
        case .formData(let id): return "/api/applications/\(id)/form-data"
        case .update(let id, _): return "/api/applications/\(id)"
        case .delete(let id): return "/api/applications/\(id)"
        case .generateNarratives(let id, _): return "/api/applications/\(id)/generate-narratives"
        case .downloadPDF(let id): return "/api/applications/\(id)/pdf"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .list, .detail, .formData, .downloadPDF: return .get
        case .create, .generateNarratives: return .post
        case .update: return .patch
        case .delete: return .delete
        }
    }

    var queryItems: [URLQueryItem]? {
        switch self {
        case .list(let status):
            guard let status = status else { return nil }
            return [URLQueryItem(name: "status", value: status.rawValue)]
        case .generateNarratives(_, let summary):
            guard let summary = summary else { return nil }
            return [URLQueryItem(name: "project_summary", value: summary)]
        default:
            return nil
        }
    }

    var body: Data? {
        switch self {
        case .create(let programId): return try? sharedEncoder.encode(["program_id": programId])
        case .update(_, let request): return try? sharedEncoder.encode(request)
        default: return nil
        }
    }
}

// MARK: - Eligibility Endpoints
enum EligibilityEndpoint: APIEndpoint {
    case checkAll
    case checkProgram(programId: String)

    var path: String {
        switch self {
        case .checkAll: return "/api/eligibility/check"
        case .checkProgram(let id): return "/api/eligibility/check/\(id)"
        }
    }

    var method: HTTPMethod { .get }
}

// MARK: - Notification Endpoints
enum NotificationEndpoints: APIEndpoint {
    case registerDevice(token: String, platform: String)
    case unregisterDevice(token: String)
    case getPreferences
    case updatePreferences(NotificationPreferences)

    var path: String {
        switch self {
        case .registerDevice: return "/api/notifications/device"
        case .unregisterDevice: return "/api/notifications/device"
        case .getPreferences: return "/api/notifications/preferences"
        case .updatePreferences: return "/api/notifications/preferences"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .registerDevice: return .post
        case .unregisterDevice: return .delete
        case .getPreferences: return .get
        case .updatePreferences: return .patch
        }
    }

    var body: Data? {
        switch self {
        case .registerDevice(let token, let platform):
            return try? sharedEncoder.encode([
                "device_token": token,
                "platform": platform
            ])
        case .unregisterDevice(let token):
            return try? sharedEncoder.encode(["device_token": token])
        case .updatePreferences(let prefs):
            return try? sharedEncoder.encode(prefs)
        default:
            return nil
        }
    }
}

// MARK: - Notification Models
struct NotificationPreferences: Codable {
    var deadlineReminders: Bool
    var applicationUpdates: Bool
    var newGrantAlerts: Bool
    var reminderDaysBefore: [Int]

    init(
        deadlineReminders: Bool = true,
        applicationUpdates: Bool = true,
        newGrantAlerts: Bool = false,
        reminderDaysBefore: [Int] = [7, 3, 1]
    ) {
        self.deadlineReminders = deadlineReminders
        self.applicationUpdates = applicationUpdates
        self.newGrantAlerts = newGrantAlerts
        self.reminderDaysBefore = reminderDaysBefore
    }
}
