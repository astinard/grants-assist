import XCTest
@testable import GrantsAssist

final class GrantCategoryTests: XCTestCase {

    func testCategoryDisplayNames() {
        XCTAssertEqual(GrantCategory.healthcare.displayName, "Healthcare")
        XCTAssertEqual(GrantCategory.smallBusiness.displayName, "Small Business")
        XCTAssertEqual(GrantCategory.education.displayName, "Education")
        XCTAssertEqual(GrantCategory.nonprofit.displayName, "Nonprofit")
        XCTAssertEqual(GrantCategory.agriculture.displayName, "Agriculture")
        XCTAssertEqual(GrantCategory.technology.displayName, "Technology")
        XCTAssertEqual(GrantCategory.housing.displayName, "Housing")
    }

    func testCategoryIcons() {
        XCTAssertEqual(GrantCategory.healthcare.icon, "heart.circle.fill")
        XCTAssertEqual(GrantCategory.smallBusiness.icon, "building.2.fill")
        XCTAssertEqual(GrantCategory.education.icon, "graduationcap.fill")
        XCTAssertEqual(GrantCategory.agriculture.icon, "leaf.fill")
        XCTAssertEqual(GrantCategory.technology.icon, "cpu.fill")
    }

    func testCategoryRawValues() {
        XCTAssertEqual(GrantCategory.healthcare.rawValue, "healthcare")
        XCTAssertEqual(GrantCategory.smallBusiness.rawValue, "small_business")
        XCTAssertEqual(GrantCategory.education.rawValue, "education")
    }
}

final class GrantProgramTests: XCTestCase {

    func testGrantProgramDecoding() throws {
        let json = """
        {
            "id": "usda-123",
            "name": "USDA Rural Development Grant",
            "agency": "USDA",
            "category": "agriculture",
            "min_award": 5000.0,
            "max_award": 50000.0,
            "match_required": 0.25,
            "description": "Grant for rural development projects",
            "eligibility_summary": "Must be in rural area",
            "required_fields": null,
            "deadline": "2024-06-30T23:59:59.000000",
            "rolling_deadline": false,
            "program_url": "https://example.com/grant",
            "application_url": null,
            "is_active": true
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let program = try decoder.decode(GrantProgram.self, from: json)

        XCTAssertEqual(program.id, "usda-123")
        XCTAssertEqual(program.name, "USDA Rural Development Grant")
        XCTAssertEqual(program.agency, "USDA")
        XCTAssertEqual(program.category, .agriculture)
        XCTAssertEqual(program.minAward, 5000.0)
        XCTAssertEqual(program.maxAward, 50000.0)
        XCTAssertEqual(program.matchRequired, 0.25)
        XCTAssertFalse(program.isRollingDeadline)
        XCTAssertTrue(program.isActiveProgram)
    }

    func testAwardRangeFormatting() throws {
        let json = """
        {
            "id": "test-1",
            "name": "Test Grant",
            "agency": "Test",
            "category": "education",
            "min_award": 1000.0,
            "max_award": 25000.0,
            "match_required": null,
            "description": null,
            "eligibility_summary": null,
            "required_fields": null,
            "deadline": null,
            "rolling_deadline": true,
            "program_url": null,
            "application_url": null,
            "is_active": true
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let program = try decoder.decode(GrantProgram.self, from: json)

        // Award range should be formatted
        XCTAssertFalse(program.awardRange.isEmpty)
        XCTAssertTrue(program.awardRange.contains("$"))
    }

    func testRollingDeadline() throws {
        let json = """
        {
            "id": "rolling-1",
            "name": "Rolling Grant",
            "agency": "Agency",
            "category": "nonprofit",
            "min_award": null,
            "max_award": null,
            "match_required": null,
            "description": null,
            "eligibility_summary": null,
            "required_fields": null,
            "deadline": null,
            "rolling_deadline": true,
            "program_url": null,
            "application_url": null,
            "is_active": true
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let program = try decoder.decode(GrantProgram.self, from: json)

        XCTAssertTrue(program.isRollingDeadline)
        XCTAssertEqual(program.deadlineText, "Rolling")
    }
}
