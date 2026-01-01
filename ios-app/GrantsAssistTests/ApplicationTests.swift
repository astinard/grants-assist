import XCTest
@testable import GrantsAssist

final class ApplicationStatusTests: XCTestCase {

    func testStatusDisplayNames() {
        XCTAssertEqual(ApplicationStatus.draft.displayName, "Draft")
        XCTAssertEqual(ApplicationStatus.inProgress.displayName, "In Progress")
        XCTAssertEqual(ApplicationStatus.readyToSubmit.displayName, "Ready to Submit")
        XCTAssertEqual(ApplicationStatus.submitted.displayName, "Submitted")
        XCTAssertEqual(ApplicationStatus.underReview.displayName, "Under Review")
        XCTAssertEqual(ApplicationStatus.approved.displayName, "Approved")
        XCTAssertEqual(ApplicationStatus.denied.displayName, "Denied")
    }

    func testStatusIcons() {
        XCTAssertEqual(ApplicationStatus.draft.icon, "doc")
        XCTAssertEqual(ApplicationStatus.submitted.icon, "paperplane.fill")
        XCTAssertEqual(ApplicationStatus.approved.icon, "checkmark.seal.fill")
        XCTAssertEqual(ApplicationStatus.denied.icon, "xmark.circle.fill")
    }

    func testIsEditable() {
        // Editable statuses
        XCTAssertTrue(ApplicationStatus.draft.isEditable)
        XCTAssertTrue(ApplicationStatus.inProgress.isEditable)
        XCTAssertTrue(ApplicationStatus.readyToSubmit.isEditable)

        // Non-editable statuses
        XCTAssertFalse(ApplicationStatus.submitted.isEditable)
        XCTAssertFalse(ApplicationStatus.underReview.isEditable)
        XCTAssertFalse(ApplicationStatus.approved.isEditable)
        XCTAssertFalse(ApplicationStatus.denied.isEditable)
    }

    func testIsFinal() {
        XCTAssertTrue(ApplicationStatus.approved.isFinal)
        XCTAssertTrue(ApplicationStatus.denied.isFinal)

        XCTAssertFalse(ApplicationStatus.draft.isFinal)
        XCTAssertFalse(ApplicationStatus.submitted.isFinal)
    }
}

final class ApplicationModelTests: XCTestCase {

    func testApplicationDecoding() throws {
        let json = """
        {
            "id": "app-123",
            "program_id": "prog-456",
            "program_name": "Test Grant",
            "status": "in_progress",
            "completeness_score": 75.5,
            "created_at": "2024-01-15T10:30:00.000000",
            "updated_at": "2024-01-16T14:45:00.000000",
            "submitted_at": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let application = try decoder.decode(Application.self, from: json)

        XCTAssertEqual(application.id, "app-123")
        XCTAssertEqual(application.programId, "prog-456")
        XCTAssertEqual(application.programName, "Test Grant")
        XCTAssertEqual(application.status, .inProgress)
        XCTAssertEqual(application.completenessScore, 75.5)
        XCTAssertNil(application.submittedAt)
    }

    func testApplicationWithSubmittedDate() throws {
        let json = """
        {
            "id": "app-789",
            "program_id": "prog-101",
            "program_name": "Submitted Grant",
            "status": "submitted",
            "completeness_score": 100.0,
            "created_at": "2024-01-10T08:00:00.000000",
            "updated_at": "2024-01-20T16:30:00.000000",
            "submitted_at": "2024-01-20T16:30:00.000000"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let application = try decoder.decode(Application.self, from: json)

        XCTAssertEqual(application.status, .submitted)
        XCTAssertNotNil(application.submittedAt)
    }
}

final class AnyCodableTests: XCTestCase {

    func testStringValue() {
        let value = AnyCodable("test string")
        XCTAssertEqual(value.value as? String, "test string")
    }

    func testIntValue() {
        let value = AnyCodable(42)
        XCTAssertEqual(value.value as? Int, 42)
    }

    func testBoolValue() {
        let value = AnyCodable(true)
        XCTAssertEqual(value.value as? Bool, true)
    }

    func testEquality() {
        let value1 = AnyCodable("test")
        let value2 = AnyCodable("test")
        let value3 = AnyCodable("different")

        XCTAssertEqual(value1, value2)
        XCTAssertNotEqual(value1, value3)
    }
}
