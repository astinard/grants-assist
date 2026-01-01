import XCTest
@testable import GrantsAssist

final class MatchLevelTests: XCTestCase {

    func testMatchLevelDisplayNames() {
        XCTAssertEqual(EligibilityResult.MatchLevel.excellent.displayName, "Excellent Match")
        XCTAssertEqual(EligibilityResult.MatchLevel.good.displayName, "Good Match")
        XCTAssertEqual(EligibilityResult.MatchLevel.fair.displayName, "Fair Match")
        XCTAssertEqual(EligibilityResult.MatchLevel.poor.displayName, "Low Match")
    }

    func testMatchLevelIcons() {
        XCTAssertEqual(EligibilityResult.MatchLevel.excellent.icon, "star.fill")
        XCTAssertEqual(EligibilityResult.MatchLevel.good.icon, "hand.thumbsup.fill")
        XCTAssertEqual(EligibilityResult.MatchLevel.fair.icon, "questionmark.circle")
        XCTAssertEqual(EligibilityResult.MatchLevel.poor.icon, "exclamationmark.triangle")
    }
}

final class EligibilityResultTests: XCTestCase {

    func testEligibilityResultDecoding() throws {
        let json = """
        {
            "program_id": "test-program",
            "program_name": "Test Grant Program",
            "match_score": 85,
            "eligible": true,
            "missing_requirements": [],
            "recommendations": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let result = try decoder.decode(EligibilityResult.self, from: json)

        XCTAssertEqual(result.programId, "test-program")
        XCTAssertEqual(result.programName, "Test Grant Program")
        XCTAssertTrue(result.eligible)
        XCTAssertEqual(result.matchScore, 85)
        XCTAssertTrue(result.missingRequirements.isEmpty)
    }

    func testMatchLevelFromScore() throws {
        // Excellent: 80+
        let excellentJson = """
        {"program_id": "1", "program_name": "A", "match_score": 90, "eligible": true, "missing_requirements": [], "recommendations": null}
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let excellent = try decoder.decode(EligibilityResult.self, from: excellentJson)
        XCTAssertEqual(excellent.matchLevel, .excellent)

        // Good: 60-79
        let goodJson = """
        {"program_id": "2", "program_name": "B", "match_score": 70, "eligible": true, "missing_requirements": [], "recommendations": null}
        """.data(using: .utf8)!

        let good = try decoder.decode(EligibilityResult.self, from: goodJson)
        XCTAssertEqual(good.matchLevel, .good)

        // Fair: 40-59
        let fairJson = """
        {"program_id": "3", "program_name": "C", "match_score": 50, "eligible": false, "missing_requirements": ["EIN required"], "recommendations": null}
        """.data(using: .utf8)!

        let fair = try decoder.decode(EligibilityResult.self, from: fairJson)
        XCTAssertEqual(fair.matchLevel, .fair)

        // Poor: <40
        let poorJson = """
        {"program_id": "4", "program_name": "D", "match_score": 20, "eligible": false, "missing_requirements": ["Many requirements missing"], "recommendations": null}
        """.data(using: .utf8)!

        let poor = try decoder.decode(EligibilityResult.self, from: poorJson)
        XCTAssertEqual(poor.matchLevel, .poor)
    }

    func testMatchScoreText() throws {
        let json = """
        {"program_id": "1", "program_name": "Test", "match_score": 75, "eligible": true, "missing_requirements": [], "recommendations": null}
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let result = try decoder.decode(EligibilityResult.self, from: json)
        XCTAssertEqual(result.matchScoreText, "75%")
    }

    func testMissingRequirements() throws {
        let json = """
        {
            "program_id": "incomplete-app",
            "program_name": "Incomplete Grant",
            "match_score": 45,
            "eligible": false,
            "missing_requirements": ["EIN required", "SAM.gov registration needed", "Address incomplete"],
            "recommendations": ["Complete your profile", "Register on SAM.gov"]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let result = try decoder.decode(EligibilityResult.self, from: json)

        XCTAssertFalse(result.eligible)
        XCTAssertEqual(result.missingRequirements.count, 3)
        XCTAssertTrue(result.missingRequirements.contains("EIN required"))
        XCTAssertEqual(result.recommendations?.count, 2)
    }
}

final class EligibilityCheckResponseTests: XCTestCase {

    func testResponseDecoding() throws {
        let json = """
        {
            "results": [
                {"program_id": "prog-1", "program_name": "Grant 1", "match_score": 95, "eligible": true, "missing_requirements": [], "recommendations": null},
                {"program_id": "prog-2", "program_name": "Grant 2", "match_score": 80, "eligible": true, "missing_requirements": [], "recommendations": null},
                {"program_id": "prog-3", "program_name": "Grant 3", "match_score": 30, "eligible": false, "missing_requirements": ["EIN"], "recommendations": null}
            ],
            "profile_completeness": 75
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(EligibilityCheckResponse.self, from: json)

        XCTAssertEqual(response.results.count, 3)
        XCTAssertEqual(response.profileCompleteness, 75)
    }

    func testTopMatches() throws {
        let json = """
        {
            "results": [
                {"program_id": "1", "program_name": "A", "match_score": 90, "eligible": true, "missing_requirements": [], "recommendations": null},
                {"program_id": "2", "program_name": "B", "match_score": 70, "eligible": true, "missing_requirements": [], "recommendations": null},
                {"program_id": "3", "program_name": "C", "match_score": 50, "eligible": false, "missing_requirements": [], "recommendations": null},
                {"program_id": "4", "program_name": "D", "match_score": 30, "eligible": false, "missing_requirements": [], "recommendations": null}
            ],
            "profile_completeness": 80
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(EligibilityCheckResponse.self, from: json)

        // Top matches are those with score >= 60
        XCTAssertEqual(response.topMatches.count, 2)
        XCTAssertTrue(response.hasGoodMatches)
    }

    func testNoGoodMatches() throws {
        let json = """
        {
            "results": [
                {"program_id": "1", "program_name": "A", "match_score": 50, "eligible": false, "missing_requirements": [], "recommendations": null},
                {"program_id": "2", "program_name": "B", "match_score": 30, "eligible": false, "missing_requirements": [], "recommendations": null}
            ],
            "profile_completeness": 40
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(EligibilityCheckResponse.self, from: json)

        XCTAssertFalse(response.hasGoodMatches)
        XCTAssertTrue(response.topMatches.isEmpty)
    }
}
