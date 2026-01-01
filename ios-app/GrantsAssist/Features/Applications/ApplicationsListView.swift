import SwiftUI

struct ApplicationsListView: View {
    @StateObject private var viewModel = ApplicationsViewModel()
    @State private var selectedFilter: ApplicationStatus?
    @State private var showingApplication: Application?

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.applications.isEmpty && !viewModel.isLoading {
                    emptyState
                } else {
                    applicationsList
                }
            }
            .navigationTitle("Applications")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            selectedFilter = nil
                            Task { await viewModel.loadApplications(status: nil) }
                        } label: {
                            HStack {
                                Text("All")
                                if selectedFilter == nil {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }

                        ForEach([ApplicationStatus.draft, .inProgress, .submitted], id: \.self) { status in
                            Button {
                                selectedFilter = status
                                Task { await viewModel.loadApplications(status: status) }
                            } label: {
                                HStack {
                                    Text(status.displayName)
                                    if selectedFilter == status {
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        Image(systemName: "line.3.horizontal.decrease.circle")
                    }
                }
            }
            .refreshable {
                await viewModel.loadApplications(status: selectedFilter)
            }
            .task {
                if viewModel.applications.isEmpty {
                    await viewModel.loadApplications(status: nil)
                }
            }
            .sheet(item: $showingApplication) { application in
                ApplicationDetailView(application: application)
            }
        }
    }

    // MARK: - Applications List

    private var applicationsList: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                if viewModel.isLoading {
                    ForEach(0..<3, id: \.self) { _ in
                        ApplicationCardPlaceholder()
                    }
                } else {
                    ForEach(viewModel.applications) { application in
                        ApplicationCard(application: application)
                            .onTapGesture {
                                showingApplication = application
                            }
                            .contextMenu {
                                if application.status.isEditable {
                                    Button(role: .destructive) {
                                        Task { await viewModel.deleteApplication(application) }
                                    } label: {
                                        Label("Delete", systemImage: "trash")
                                    }
                                }
                            }
                    }
                }
            }
            .padding()
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 20) {
            Image(systemName: "doc.text")
                .font(.system(size: 64))
                .foregroundStyle(.secondary)

            Text("No Applications Yet")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Start by discovering grants that match your profile")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Button {
                // Navigate to discover tab
            } label: {
                HStack {
                    Image(systemName: "magnifyingglass")
                    Text("Discover Grants")
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 12)
                .background(Color.accentColor)
                .foregroundStyle(.white)
                .cornerRadius(12)
            }
        }
        .padding()
    }
}

// MARK: - Application Card

struct ApplicationCard: View {
    let application: Application

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(application.programName)
                        .font(.headline)
                        .lineLimit(1)
                }

                Spacer()

                // Status Badge
                StatusBadge(status: application.status)
            }

            // Progress Bar
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("Completeness")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(Int(application.completenessScore))%")
                        .font(.caption)
                        .fontWeight(.medium)
                }

                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color(.systemGray5))

                        RoundedRectangle(cornerRadius: 4)
                            .fill(progressColor)
                            .frame(width: geometry.size.width * CGFloat(application.completenessScore) / 100)
                    }
                }
                .frame(height: 6)
            }

            // Footer
            HStack {
                Label(application.lastModifiedText, systemImage: "clock")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                if let submitted = application.submittedText {
                    Label("Submitted \(submitted)", systemImage: "paperplane")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 8, x: 0, y: 2)
    }

    private var progressColor: Color {
        switch application.completenessScore {
        case 80...100: return .green
        case 50..<80: return .orange
        default: return .red
        }
    }
}

// MARK: - Status Badge

struct StatusBadge: View {
    let status: ApplicationStatus

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: status.icon)
            Text(status.displayName)
        }
        .font(.caption)
        .fontWeight(.medium)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(backgroundColor)
        .foregroundStyle(foregroundColor)
        .cornerRadius(12)
    }

    private var backgroundColor: Color {
        switch status {
        case .draft: return Color(.systemGray5)
        case .inProgress: return Color.blue.opacity(0.15)
        case .readyToSubmit: return Color.orange.opacity(0.15)
        case .submitted: return Color.purple.opacity(0.15)
        case .underReview: return Color.yellow.opacity(0.15)
        case .approved: return Color.green.opacity(0.15)
        case .denied: return Color.red.opacity(0.15)
        }
    }

    private var foregroundColor: Color {
        switch status {
        case .draft: return .secondary
        case .inProgress: return .blue
        case .readyToSubmit: return .orange
        case .submitted: return .purple
        case .underReview: return .yellow
        case .approved: return .green
        case .denied: return .red
        }
    }
}

// MARK: - Placeholder

struct ApplicationCardPlaceholder: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color(.systemGray5))
                        .frame(width: 180, height: 18)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color(.systemGray5))
                        .frame(width: 100, height: 14)
                }
                Spacer()
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color(.systemGray5))
                    .frame(width: 80, height: 28)
            }

            RoundedRectangle(cornerRadius: 4)
                .fill(Color(.systemGray5))
                .frame(height: 6)

            HStack {
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 80, height: 12)
                Spacer()
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .redacted(reason: .placeholder)
    }
}

#Preview {
    ApplicationsListView()
        .environmentObject(AuthService.shared)
        .environmentObject(AppState())
}
