import SwiftUI

struct AIWriterView: View {
    @StateObject private var viewModel: AIWriterViewModel
    @State private var selectedSection: SectionStatus?
    @State private var showingGenerateAll = false
    @State private var selectedTone = "professional"

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
            .disabled(viewModel.isGenerating)
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
