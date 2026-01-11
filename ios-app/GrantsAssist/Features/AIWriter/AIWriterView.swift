import SwiftUI

struct AIWriterView: View {
    @StateObject private var viewModel: AIWriterViewModel
    @State private var selectedSection: SectionStatus?
    @State private var showingGenerateAll = false
    @State private var showingFullAppSheet = false
    @State private var showingFullAppResult = false
    @State private var selectedTone = "professional"
    @State private var projectTitle = ""
    @State private var projectSummary = ""

    init(applicationId: String, programName: String) {
        _viewModel = StateObject(wrappedValue: AIWriterViewModel(
            applicationId: applicationId,
            programName: programName
        ))
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Progress Header
                progressHeader

                // Quick Actions
                quickActions

                // Sections List
                sectionsList
            }
            .padding()
        }
        .navigationTitle("AI Writer")
        .navigationBarTitleDisplayMode(.large)
        .task {
            await viewModel.loadStatus()
        }
        .sheet(item: $selectedSection) { section in
            SectionEditorView(
                viewModel: viewModel,
                sectionType: section.sectionType
            )
        }
        .confirmationDialog("Generate All Sections", isPresented: $showingGenerateAll) {
            Button("Professional Tone") {
                Task {
                    await viewModel.generateAllSections(tone: "professional")
                }
            }
            Button("Compelling Tone") {
                Task {
                    await viewModel.generateAllSections(tone: "compelling")
                }
            }
            Button("Data-Driven Tone") {
                Task {
                    await viewModel.generateAllSections(tone: "data_driven")
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will generate all 10 sections. Choose a writing tone:")
        }
        .overlay {
            if viewModel.isGenerating {
                generatingOverlay
            } else if viewModel.isGeneratingFullApp {
                fullAppGeneratingOverlay
            }
        }
        .sheet(isPresented: $showingFullAppSheet) {
            FullAppInputSheet(
                programName: viewModel.programName,
                projectTitle: $projectTitle,
                projectSummary: $projectSummary
            ) {
                showingFullAppSheet = false
                Task {
                    await viewModel.generateFullApplication(
                        projectTitle: projectTitle,
                        projectSummary: projectSummary
                    )
                    if viewModel.fullApplicationResult != nil {
                        showingFullAppResult = true
                    }
                }
            }
        }
        .sheet(isPresented: $showingFullAppResult) {
            if let result = viewModel.fullApplicationResult {
                FullAppResultView(result: result)
            }
        }
    }

    // MARK: - Progress Header

    private var progressHeader: some View {
        VStack(spacing: 16) {
            // Progress Ring
            ZStack {
                Circle()
                    .stroke(Color.gray.opacity(0.2), lineWidth: 12)

                Circle()
                    .trim(from: 0, to: CGFloat(viewModel.progress) / 100)
                    .stroke(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        style: StrokeStyle(lineWidth: 12, lineCap: .round)
                    )
                    .rotationEffect(.degrees(-90))

                VStack(spacing: 4) {
                    Text("\(viewModel.progress)%")
                        .font(.title)
                        .fontWeight(.bold)

                    Text("Complete")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 120, height: 120)

            // Stats
            HStack(spacing: 24) {
                statItem(
                    value: "\(viewModel.completedSections)/\(viewModel.sections.count)",
                    label: "Sections"
                )

                statItem(
                    value: "\(viewModel.totalWords)",
                    label: "Words"
                )

                statItem(
                    value: String(format: "%.1f", viewModel.estimatedPages),
                    label: "Pages"
                )

                if viewModel.averageQuality > 0 {
                    statItem(
                        value: String(format: "%.0f", viewModel.averageQuality),
                        label: "Quality"
                    )
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
    }

    private func statItem(value: String, label: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.headline)
                .fontWeight(.semibold)

            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Quick Actions

    private var quickActions: some View {
        VStack(spacing: 12) {
            // AI Agent - Full Application Generation
            Button {
                showingFullAppSheet = true
            } label: {
                HStack {
                    Image(systemName: "wand.and.stars")
                        .font(.title2)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("AI Agent: Write Full Application")
                            .fontWeight(.semibold)
                        Text("Let AI research & write everything")
                            .font(.caption)
                            .opacity(0.9)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                }
                .padding()
                .background(
                    LinearGradient(
                        colors: [.purple, .pink],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .foregroundStyle(.white)
                .cornerRadius(12)
            }
            .disabled(viewModel.isGenerating || viewModel.isGeneratingFullApp)

            // Section-by-section generation
            Button {
                showingGenerateAll = true
            } label: {
                HStack {
                    Image(systemName: "sparkles")
                    Text("Generate All Sections")
                    Spacer()
                    Image(systemName: "chevron.right")
                }
                .padding()
                .background(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .foregroundStyle(.white)
                .cornerRadius(12)
            }
            .disabled(viewModel.isGenerating || viewModel.isGeneratingFullApp)
        }
    }

    // MARK: - Sections List

    private var sectionsList: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Sections")
                .font(.headline)
                .padding(.horizontal, 4)

            ForEach(viewModel.sections) { section in
                SectionCard(
                    section: section,
                    info: viewModel.getSectionInfo(for: section.sectionType)
                ) {
                    selectedSection = section
                }
            }
        }
    }

    // MARK: - Generating Overlay

    private var generatingOverlay: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()

            VStack(spacing: 20) {
                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.white)

                Text("Generating with AI...")
                    .font(.headline)
                    .foregroundStyle(.white)

                Text("This may take a moment")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.8))
            }
            .padding(40)
            .background(.ultraThinMaterial)
            .cornerRadius(20)
        }
    }

    // MARK: - Full App Generating Overlay

    private var fullAppGeneratingOverlay: some View {
        ZStack {
            Color.black.opacity(0.5)
                .ignoresSafeArea()

            VStack(spacing: 24) {
                // Animated icon
                Image(systemName: "wand.and.stars")
                    .font(.system(size: 50))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.purple, .pink],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                VStack(spacing: 8) {
                    Text("AI Agent Working")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)

                    Text(viewModel.generationProgress)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.9))

                    Text("This may take 30-60 seconds")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                }

                ProgressView()
                    .scaleEffect(1.2)
                    .tint(.white)
            }
            .padding(40)
            .background(.ultraThinMaterial)
            .cornerRadius(24)
        }
    }
}

// MARK: - Full App Input Sheet

struct FullAppInputSheet: View {
    let programName: String
    @Binding var projectTitle: String
    @Binding var projectSummary: String
    let onGenerate: () -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 12) {
                        Image(systemName: "wand.and.stars")
                            .font(.system(size: 60))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [.purple, .pink],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )

                        Text("AI Grant Writer Agent")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text("The AI will research the grant requirements, gather data, and write a complete professional application.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(.top)

                    // Grant info
                    HStack {
                        Image(systemName: "doc.text.fill")
                            .foregroundStyle(.blue)
                        Text(programName)
                            .fontWeight(.medium)
                        Spacer()
                    }
                    .padding()
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(12)

                    // Input fields
                    VStack(alignment: .leading, spacing: 16) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Project Title")
                                .font(.headline)
                            TextField("Enter your project title", text: $projectTitle)
                                .textFieldStyle(.roundedBorder)
                        }

                        VStack(alignment: .leading, spacing: 8) {
                            Text("Project Summary")
                                .font(.headline)
                            Text("Briefly describe what your project will accomplish")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            TextEditor(text: $projectSummary)
                                .frame(minHeight: 120)
                                .padding(8)
                                .background(Color(.systemGray6))
                                .cornerRadius(8)
                        }
                    }

                    // Time warning
                    HStack {
                        Image(systemName: "clock.fill")
                            .foregroundStyle(.orange)
                        Text("Generation takes 30-60 seconds")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.orange.opacity(0.1))
                    .cornerRadius(12)
                }
                .padding()
            }
            .navigationTitle("Generate Application")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Generate") {
                        onGenerate()
                    }
                    .fontWeight(.semibold)
                    .disabled(projectTitle.isEmpty || projectSummary.isEmpty)
                }
            }
        }
    }
}

// MARK: - Full App Result View

struct FullAppResultView: View {
    let result: FullApplicationResponse

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Success header
                    VStack(spacing: 12) {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 60))
                            .foregroundStyle(.green)

                        Text("Application Generated!")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text(result.message)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.bottom)

                    // Stats
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 16) {
                        StatBox(value: "\(result.wordCount)", label: "Words")
                        StatBox(value: "\(result.sectionCount)", label: "Sections")
                        StatBox(value: String(format: "%.0fs", result.generationTimeSeconds), label: "Time")
                    }

                    Divider()

                    // Sections generated
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Sections Generated")
                            .font(.headline)

                        ForEach(result.sections, id: \.self) { section in
                            HStack {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.green)
                                Text(section.replacingOccurrences(of: "_", with: " ").capitalized)
                                Spacer()
                            }
                            .padding(.vertical, 4)
                        }
                    }

                    Divider()

                    // Full application preview
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Application Preview")
                            .font(.headline)

                        Text(result.fullApplication)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(20)
                    }
                }
                .padding()
            }
            .navigationTitle("Result")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
    }
}

// MARK: - Stat Box

struct StatBox: View {
    let value: String
    let label: String

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - Section Card

struct SectionCard: View {
    let section: SectionStatus
    let info: SectionInfo?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                // Status Icon
                ZStack {
                    Circle()
                        .fill(statusColor.opacity(0.15))
                        .frame(width: 44, height: 44)

                    Image(systemName: statusIcon)
                        .foregroundStyle(statusColor)
                }

                // Info
                VStack(alignment: .leading, spacing: 4) {
                    Text(section.title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.primary)

                    if section.hasContent {
                        HStack(spacing: 8) {
                            Text("\(section.wordCount) words")

                            if let score = section.qualityScore {
                                Text("\(Int(score))% quality")
                                    .foregroundStyle(qualityColor(score))
                            }
                        }
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    } else if let info = info {
                        Text(info.description)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }

                Spacer()

                // Action indicator
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }

    private var statusColor: Color {
        if section.hasContent {
            if let score = section.qualityScore, score >= 80 {
                return .green
            }
            return .blue
        }
        return .gray
    }

    private var statusIcon: String {
        if section.hasContent {
            if let score = section.qualityScore, score >= 80 {
                return "checkmark.circle.fill"
            }
            return "doc.text.fill"
        }
        return "doc.badge.plus"
    }

    private func qualityColor(_ score: Double) -> Color {
        if score >= 80 { return .green }
        if score >= 60 { return .orange }
        return .red
    }
}

#Preview {
    NavigationStack {
        AIWriterView(applicationId: "test-123", programName: "Test Grant")
    }
}
