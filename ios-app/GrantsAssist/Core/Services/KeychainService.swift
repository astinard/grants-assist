import Foundation
import Security

final class KeychainService {
    static let shared = KeychainService()

    private init() {}

    // MARK: - Access Token

    func saveAccessToken(_ token: String) {
        save(token, forKey: Configuration.KeychainKey.accessToken)
    }

    func getAccessToken() -> String? {
        get(forKey: Configuration.KeychainKey.accessToken)
    }

    func deleteAccessToken() {
        delete(forKey: Configuration.KeychainKey.accessToken)
    }

    // MARK: - User ID

    func saveUserId(_ userId: String) {
        save(userId, forKey: Configuration.KeychainKey.userId)
    }

    func getUserId() -> String? {
        get(forKey: Configuration.KeychainKey.userId)
    }

    func deleteUserId() {
        delete(forKey: Configuration.KeychainKey.userId)
    }

    // MARK: - Clear All

    func clearTokens() {
        deleteAccessToken()
        deleteUserId()
    }

    // MARK: - Private Methods

    private func save(_ value: String, forKey key: String) {
        guard let data = value.data(using: .utf8) else { return }

        // Delete existing item first
        delete(forKey: key)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]

        SecItemAdd(query as CFDictionary, nil)
    }

    private func get(forKey key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let value = String(data: data, encoding: .utf8) else {
            return nil
        }

        return value
    }

    private func delete(forKey key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]

        SecItemDelete(query as CFDictionary)
    }
}
