import SwiftUI

struct SectionEditorView: View {
    @ObservedObject var viewModel: AIWriterViewModel
    @Environment(\.dismiss) private var dismiss

    let sectionType: String

    @State private var content: String = ""
    @State private var isEditing = false
    @State private var showingToneSelector = false
    @State private var showingImprovementSheet = false
    @State private var selectedTone = "professional"
    @State private var improvementFocus = ""
    @State private var additionalContext = ""

    @FocusState private var isTextFieldFocused: Bool

    private var sectionInfo: SectionInfo? {
        viewModel.getSectionInfo(for: sectionType)
    }

    private var sectionStatus: SectionStatus? {
        viewModel.sections.first { $0.sectionType == sectionType }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Section Info Header
                    sectionHeader

                    // Content Area
                    if viewModel.isLoading && content.isEmpty {
                        loadingView
                    } else if content.isEmpty && !isEditing {
                        emptyState
                    } else {
                        contentEditor
                    }

                    // Quality Feedback
                    if let result = viewModel.generationResult,
                       result.sectionType == sectionType {
                        qualityFeedback(result)
                    }

                    // Key Elements Checklist
                    if let info = sectionInfo {
                        keyElementsChecklist(info.keyElements)
                    }
                }
                .padding()
            }
            .navigationTitle(sectionInfo?.title ?? "Section")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .primaryAction) {
                    if isEditing {
                        Button("Save") {
                            Task {
                                await viewModel.saveSection(
                                    sectionType: sectionType,
                                    content: content
                                )
                                isEditing = false
                            }
                        }
                        .fontWeight(.semibold)
                    }
                }
            }
            .task {
                await viewModel.loadSectionContent(sectionType: sectionType)
                if let section = viewModel.currentSection {
                    content = section.content ?? ""
                }
            }
            .sheet(isPresented: $showingToneSelector) {
                toneSelectorSheet
            }
            .sheet(isPresented: $showingImprovementSheet) {
                improvementSheet
            }
            .overlay {
                if viewModel.isGenerating {
                    generatingOverlay
                }
            }
        }
    }

    // MARK: - Section Header

    private var sectionHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let info = sectionInfo {
                Text(info.description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                HStack {
                    Label("\(info.minWords)-\(info.maxWords) words", systemImage: "text.word.spacing")

                    if let status = sectionStatus, status.hasContent {
                        Spacer()
                        Label("\(status.wordCount) written", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                    }
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    // MARK: - Loading View

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
            Text("Loading content...")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(40)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 20) {
            Image(systemName: "doc.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("No content yet")
                .font(.headline)

            Text("Generate this section with AI or write your own content")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            VStack(spacing: 12) {
                // Generate Button
                Button {
                    showingToneSelector = true
                } label: {
                    HStack {
                        Image(systemName: "sparkles")
                        Text("Generate with AI")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
                }

                // Write Manually Button
                Button {
                    isEditing = true
                    isTextFieldFocused = true
                } label: {
                    HStack {
                        Image(systemName: "pencil")
                        Text("Write Manually")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color(.systemGray6))
                    .foregroundStyle(.primary)
                    .cornerRadius(12)
                }
            }
        }
        .padding()
    }

    // MARK: - Content Editor

    private var contentEditor: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Editor Header
            HStack {
                Text("Content")
                    .font(.headline)

                Spacer()

                if !isEditing {
                    Menu {
                        Button {
                            isEditing = true
                            isTextFieldFocused = true
                        } label: {
                            Label("Edit", systemImage: "pencil")
                        }

                        Button {
                            showingToneSelector = true
                        } label: {
                            Label("Regenerate", systemImage: "arrow.clockwise")
                        }

                        Button {
                            showingImprovementSheet = true
                        } label: {
                            Label("Improve", systemImage: "wand.and.stars")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .font(.title3)
                    }
                }
            }

            // Text Editor
            if isEditing {
                TextEditor(text: $content)
                    .focused($isTextFieldFocused)
                    .frame(minHeight: 300)
                    .padding(8)
                    .background(Color(.systemGray6))
                    .cornerRadius(8)
            } else {
                Text(content)
                    .font(.body)
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.systemGray6))
                    .cornerRadius(8)
            }

            // Word Count
            HStack {
                Text("\(content.split(separator: " ").count) words")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                if isEditing {
                    Button("Cancel") {
                        // Reload original content
                        if let section = viewModel.currentSection {
                            content = section.content ?? ""
                        }
                        isEditing = false
                    }
                    .font(.caption)
                }
            }
        }
    }

    // MARK: - Quality Feedback

    private func qualityFeedback(_ result: GenerateSectionResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Quality Score")
                    .font(.headline)

                Spacer()

                Text("\(Int(result.qualityScore))%")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundStyle(qualityColor(result.qualityScore))
            }

            Text(result.qualityFeedback)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if !result.suggestions.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Suggestions")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    ForEach(result.suggestions, id: \.self) { suggestion in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: "lightbulb")
                                .foregroundStyle(.orange)
                            Text(suggestion)
                                .font(.caption)
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    // MARK: - Key Elements Checklist

    private func keyElementsChecklist(_ elements: [String]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Key Elements")
                .font(.headline)

            ForEach(elements, id: \.self) { element in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "circle")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(element)
                        .font(.subheadline)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    // MARK: - Tone Selector Sheet

    private var toneSelectorSheet: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Choose a writing tone for AI generation")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                VStack(spacing: 12) {
                    toneOption(
                        tone: "professional",
                        title: "Professional",
                        description: "Formal language suitable for federal grants",
                        icon: "briefcase.fill"
                    )

                    toneOption(
                        tone: "compelling",
                        title: "Compelling",
                        description: "Persuasive and emotionally engaging",
                        icon: "heart.fill"
                    )

                    toneOption(
                        tone: "data_driven",
                        title: "Data-Driven",
                        description: "Lead with statistics and evidence",
                        icon: "chart.bar.fill"
                    )
                }
                .padding()

                // Additional Context
                VStack(alignment: .leading, spacing: 8) {
                    Text("Additional Context (Optional)")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    TextField("Any specific details to include...", text: $additionalContext, axis: .vertical)
                        .lineLimit(3...6)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                .padding(.horizontal)

                // Generate Button
                Button {
                    showingToneSelector = false
                    Task {
                        await viewModel.generateSection(
                            sectionType: sectionType,
                            additionalContext: additionalContext.isEmpty ? nil : additionalContext,
                            tone: selectedTone
                        )
                        if let result = viewModel.generationResult {
                            content = result.content
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "sparkles")
                        Text("Generate")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
                }
                .padding()

                Spacer()
            }
            .navigationTitle("Generate Section")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        showingToneSelector = false
                    }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    private func toneOption(tone: String, title: String, description: String, icon: String) -> some View {
        Button {
            selectedTone = tone
        } label: {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(selectedTone == tone ? .white : .accentColor)
                    .frame(width: 44, height: 44)
                    .background(selectedTone == tone ? Color.accentColor : Color.accentColor.opacity(0.15))
                    .cornerRadius(10)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.primary)

                    Text(description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                if selectedTone == tone {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Color.accentColor)
                }
            }
            .padding()
            .background(selectedTone == tone ? Color.accentColor.opacity(0.1) : Color(.systemGray6))
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Improvement Sheet

    private var improvementSheet: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("What would you like to improve?")
                    .font(.headline)

                // Common improvements
                VStack(spacing: 12) {
                    improvementOption("Add more statistics and data")
                    improvementOption("Make the opening more compelling")
                    improvementOption("Strengthen the conclusion")
                    improvementOption("Use more action verbs")
                    improvementOption("Improve flow and transitions")
                }
                .padding()

                // Custom improvement
                VStack(alignment: .leading, spacing: 8) {
                    Text("Or describe your own improvement")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    TextField("What to improve...", text: $improvementFocus, axis: .vertical)
                        .lineLimit(2...4)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                .padding(.horizontal)

                // Improve Button
                Button {
                    guard !improvementFocus.isEmpty else { return }
                    showingImprovementSheet = false
                    Task {
                        await viewModel.improveSection(
                            sectionType: sectionType,
                            currentContent: content,
                            improvementFocus: improvementFocus
                        )
                        if let result = viewModel.generationResult {
                            content = result.content
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "wand.and.stars")
                        Text("Improve Section")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(improvementFocus.isEmpty ? Color.gray : Color.accentColor)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
                }
                .disabled(improvementFocus.isEmpty)
                .padding()

                Spacer()
            }
            .navigationTitle("Improve Section")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        showingImprovementSheet = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }

    private func improvementOption(_ text: String) -> some View {
        Button {
            improvementFocus = text
        } label: {
            HStack {
                Text(text)
                    .font(.subheadline)
                Spacer()
                if improvementFocus == text {
                    Image(systemName: "checkmark")
                        .foregroundStyle(Color.accentColor)
                }
            }
            .padding()
            .background(improvementFocus == text ? Color.accentColor.opacity(0.1) : Color(.systemGray6))
            .cornerRadius(8)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Generating Overlay

    private var generatingOverlay: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()

            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)

                Text("Generating with AI...")
                    .font(.headline)

                Text("This may take a moment")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(32)
            .background(.regularMaterial)
            .cornerRadius(16)
        }
    }

    // MARK: - Helpers

    private func qualityColor(_ score: Double) -> Color {
        if score >= 80 { return .green }
        if score >= 60 { return .orange }
        return .red
    }
}

#Preview {
    SectionEditorView(
        viewModel: AIWriterViewModel(applicationId: "test", programName: "Test"),
        sectionType: "statement_of_need"
    )
}
