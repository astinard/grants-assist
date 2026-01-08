import Foundation
import SwiftUI

@MainActor
final class AIWriterViewModel: ObservableObject {
    // MARK: - Published Properties

    @Published var sections: [SectionStatus] = []
    @Published var availableSections: [SectionInfo] = []
    @Published var progress: Int = 0
    @Published var totalWords: Int = 0
    @Published var estimatedPages: Double = 0

    @Published var isLoading = false
    @Published var isGenerating = false
    @Published var error: String?

    @Published var currentSection: SectionContentResponse?
    @Published var generationResult: GenerateSectionResponse?

    // MARK: - Properties

    let applicationId: String
    let programName: String

    private let service = AIWriterService.shared

    // MARK: - Computed Properties

    var completedSections: Int {
        sections.filter { $0.hasContent }.count
    }

    var averageQuality: Double {
        let scored = sections.compactMap { $0.qualityScore }
        guard !scored.isEmpty else { return 0 }
        return scored.reduce(0, +) / Double(scored.count)
    }

    // MARK: - Init

    init(applicationId: String, programName: String) {
        self.applicationId = applicationId
        self.programName = programName
    }

    // MARK: - Load Data

    func loadStatus() async {
        isLoading = true
        error = nil

        do {
            // Load available sections info
            await service.loadAvailableSections()
            availableSections = service.availableSections

            // Load current status
            let status = try await service.getWritingStatus(applicationId: applicationId)
            sections = status.sections
            progress = status.progress
            totalWords = status.totalWords
            estimatedPages = status.estimatedPages
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Generate Section

    func generateSection(
        sectionType: String,
        additionalContext: String? = nil,
        tone: String = "professional"
    ) async {
        isGenerating = true
        error = nil
        generationResult = nil

        do {
            let result = try await service.generateSection(
                applicationId: applicationId,
                sectionType: sectionType,
                additionalContext: additionalContext,
                tone: tone
            )

            generationResult = result

            // Refresh status
            await loadStatus()
        } catch {
            self.error = error.localizedDescription
        }

        isGenerating = false
    }

    // MARK: - Improve Section

    func improveSection(
        sectionType: String,
        currentContent: String,
        improvementFocus: String
    ) async {
        isGenerating = true
        error = nil

        do {
            let result = try await service.improveSection(
                applicationId: applicationId,
                sectionType: sectionType,
                currentContent: currentContent,
                improvementFocus: improvementFocus
            )

            generationResult = result

            // Refresh status
            await loadStatus()
        } catch {
            self.error = error.localizedDescription
        }

        isGenerating = false
    }

    // MARK: - Generate All

    func generateAllSections(tone: String = "professional") async {
        isGenerating = true
        error = nil

        do {
            _ = try await service.generateAllSections(
                applicationId: applicationId,
                tone: tone
            )

            // Refresh status
            await loadStatus()
        } catch {
            self.error = error.localizedDescription
        }

        isGenerating = false
    }

    // MARK: - Load Section Content

    func loadSectionContent(sectionType: String) async {
        isLoading = true
        error = nil
        currentSection = nil

        do {
            currentSection = try await service.getSectionContent(
                applicationId: applicationId,
                sectionType: sectionType
            )
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Save Section

    func saveSection(sectionType: String, content: String) async {
        isLoading = true
        error = nil

        do {
            try await service.updateSection(
                applicationId: applicationId,
                sectionType: sectionType,
                content: content
            )

            // Refresh status
            await loadStatus()
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Helpers

    func getSectionInfo(for type: String) -> SectionInfo? {
        availableSections.first { $0.type == type }
    }
}
