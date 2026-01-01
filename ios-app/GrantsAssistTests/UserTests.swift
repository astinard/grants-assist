import XCTest
@testable import GrantsAssist

final class SubscriptionTierTests: XCTestCase {

    func testDisplayNames() {
        XCTAssertEqual(SubscriptionTier.free.displayName, "Free")
        XCTAssertEqual(SubscriptionTier.pro.displayName, "Pro")
        XCTAssertEqual(SubscriptionTier.business.displayName, "Business")
    }

    func testApplicationsPerMonth() {
        XCTAssertEqual(SubscriptionTier.free.applicationsPerMonth, Configuration.SubscriptionLimits.freeApplicationsPerMonth)
        XCTAssertEqual(SubscriptionTier.pro.applicationsPerMonth, Configuration.SubscriptionLimits.proApplicationsPerMonth)
        XCTAssertEqual(SubscriptionTier.business.applicationsPerMonth, Configuration.SubscriptionLimits.businessApplicationsPerMonth)
    }

    func testPricing() {
        XCTAssertEqual(SubscriptionTier.free.price, "Free")
        XCTAssertEqual(SubscriptionTier.pro.price, "$9.99/mo")
        XCTAssertEqual(SubscriptionTier.business.price, "$29.99/mo")
    }
}

final class UserProfileTests: XCTestCase {

    func testEmptyProfileCompleteness() {
        let profile = UserProfile()
        XCTAssertEqual(profile.completenessScore, 0)
    }

    func testPartialProfileCompleteness() {
        var profile = UserProfile()
        profile.fullName = "John Doe"
        profile.organizationName = "Test Corp"
        profile.city = "Austin"
        profile.state = "TX"

        // 4 out of 10 key fields filled
        XCTAssertGreaterThan(profile.completenessScore, 0)
        XCTAssertLessThan(profile.completenessScore, 100)
    }

    func testHasBasicInfo() {
        var profile = UserProfile()
        XCTAssertFalse(profile.hasBasicInfo)

        profile.fullName = "Jane Doe"
        XCTAssertTrue(profile.hasBasicInfo)

        profile.fullName = ""
        XCTAssertFalse(profile.hasBasicInfo)
    }

    func testHasOrganizationInfo() {
        var profile = UserProfile()
        XCTAssertFalse(profile.hasOrganizationInfo)

        profile.organizationName = "Acme Inc"
        XCTAssertTrue(profile.hasOrganizationInfo)
    }

    func testHasFederalIds() {
        var profile = UserProfile()
        XCTAssertFalse(profile.hasFederalIds)

        profile.ein = "12-3456789"
        XCTAssertTrue(profile.hasFederalIds)

        profile.ein = nil
        profile.ueiNumber = "ABC123456789"
        XCTAssertTrue(profile.hasFederalIds)
    }
}

final class AuthResponseTests: XCTestCase {

    func testAuthResponseDecoding() throws {
        let json = """
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "token_type": "bearer",
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "subscription_tier": "free",
                "subscription_expires_at": null,
                "created_at": null,
                "last_login_at": null
            }
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(AuthResponse.self, from: json)

        XCTAssertEqual(response.accessToken, "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        XCTAssertEqual(response.tokenType, "bearer")
        XCTAssertEqual(response.user.id, "user-123")
        XCTAssertEqual(response.user.email, "test@example.com")
        XCTAssertEqual(response.user.subscriptionTier, .free)
    }
}
