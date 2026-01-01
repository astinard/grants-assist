import Foundation

@MainActor
final class ApplicationsViewModel: ObservableObject {
    @Published var applications: [Application] = []
    @Published var isLoading = false
    @Published var error: String?

    private let apiClient = APIClient.shared

    // MARK: - Load Applications

    func loadApplications(status: ApplicationStatus?) async {
        isLoading = true
        error = nil

        do {
            let response: ApplicationsResponse = try await apiClient.request(
                ApplicationEndpoint.list(status: status)
            )
            applications = response.applications
        } catch let apiError as APIError {
            error = apiError.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Delete Application

    func deleteApplication(_ application: Application) async {
        guard application.status.isEditable else { return }

        do {
            try await apiClient.requestVoid(
                ApplicationEndpoint.delete(applicationId: application.id)
            )

            // Remove from local list
            applications.removeAll { $0.id == application.id }
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Update Application

    func updateApplication(_ application: Application, formData: [String: AnyCodable]?, status: ApplicationStatus?) async throws -> Application {
        let request = ApplicationUpdateRequest(status: status, formData: formData)

        let updated: Application = try await apiClient.request(
            ApplicationEndpoint.update(applicationId: application.id, request: request)
        )

        // Update local list
        if let index = applications.firstIndex(where: { $0.id == application.id }) {
            applications[index] = updated
        }

        return updated
    }
}
