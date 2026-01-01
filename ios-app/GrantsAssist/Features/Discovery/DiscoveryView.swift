import SwiftUI

struct DiscoveryView: View {
    @StateObject private var viewModel = DiscoveryViewModel()
    @State private var showingProgramDetail: GrantProgram?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Search Bar
                    searchBar

                    // Category Filter
                    categoryFilter

                    // Programs List
                    programsList
                }
                .padding(.vertical)
            }
            .navigationTitle("Discover Grants")
            .refreshable {
                await viewModel.refresh()
            }
            .task {
                if viewModel.programs.isEmpty {
                    await viewModel.refresh()
                }
            }
            .sheet(item: $showingProgramDetail) { program in
                ProgramDetailView(program: program, eligibility: viewModel.eligibilityResults[program.id])
            }
        }
    }

    // MARK: - Search Bar

    private var searchBar: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)

            TextField("Search grants...", text: $viewModel.searchText)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .onSubmit {
                    Task { await viewModel.search() }
                }

            if !viewModel.searchText.isEmpty {
                Button {
                    viewModel.searchText = ""
                    Task { await viewModel.search() }
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .padding(.horizontal)
    }

    // MARK: - Category Filter

    private var categoryFilter: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                // All Categories
                CategoryChip(
                    title: "All",
                    icon: "square.grid.2x2",
                    isSelected: viewModel.selectedCategory == nil
                ) {
                    viewModel.selectCategory(nil)
                }

                ForEach(viewModel.categories) { category in
                    CategoryChip(
                        title: category.displayName,
                        icon: category.icon,
                        isSelected: viewModel.selectedCategory == category
                    ) {
                        viewModel.selectCategory(category)
                    }
                }
            }
            .padding(.horizontal)
        }
    }

    // MARK: - Programs List

    private var programsList: some View {
        LazyVStack(spacing: 16) {
            if viewModel.isLoading {
                ForEach(0..<3, id: \.self) { _ in
                    ProgramCardPlaceholder()
                }
            } else if viewModel.programs.isEmpty {
                emptyState
            } else {
                ForEach(viewModel.filteredPrograms) { program in
                    ProgramCard(
                        program: program,
                        eligibility: viewModel.eligibilityResults[program.id]
                    )
                    .onTapGesture {
                        showingProgramDetail = program
                    }
                }
            }
        }
        .padding(.horizontal)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        EmptyStateView(
            icon: "doc.text.magnifyingglass",
            title: "No grants found",
            message: "Try adjusting your search or filters"
        )
    }
}

// MARK: - Category Chip

struct CategoryChip: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.footnote)
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(isSelected ? Color.accentColor : Color(.systemGray6))
            .foregroundStyle(isSelected ? .white : .primary)
            .cornerRadius(20)
        }
    }
}

// MARK: - Program Card

struct ProgramCard: View {
    let program: GrantProgram
    let eligibility: EligibilityResult?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(program.name)
                        .font(.headline)
                        .lineLimit(2)

                    Text(program.agency)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                // Eligibility Score
                if let eligibility = eligibility {
                    EligibilityBadge(result: eligibility)
                }
            }

            // Description
            if let description = program.description {
                Text(description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            // Details Row
            HStack(spacing: 16) {
                // Award Range
                Label(program.awardRange, systemImage: "dollarsign.circle")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                // Deadline
                HStack(spacing: 4) {
                    Image(systemName: program.isDeadlineSoon ? "exclamationmark.circle.fill" : "calendar")
                        .foregroundStyle(program.isDeadlineSoon ? .orange : .secondary)
                    Text(program.deadlineText)
                        .foregroundStyle(program.isDeadlineSoon ? .orange : .secondary)
                }
                .font(.caption)
            }

            // Category Tag
            HStack {
                Image(systemName: program.category.icon)
                Text(program.category.displayName)
            }
            .font(.caption)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
        .cardStyle()
    }
}

// MARK: - Eligibility Badge

struct EligibilityBadge: View {
    let result: EligibilityResult

    var body: some View {
        VStack(spacing: 2) {
            Text("\(result.matchScore)%")
                .font(.headline)
                .fontWeight(.bold)

            Text("match")
                .font(.caption2)
        }
        .foregroundStyle(colorForLevel)
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(colorForLevel.opacity(0.15))
        .cornerRadius(12)
    }

    private var colorForLevel: Color {
        switch result.matchLevel {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .poor: return .red
        }
    }
}

// MARK: - Placeholder

struct ProgramCardPlaceholder: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color(.systemGray5))
                        .frame(width: 200, height: 20)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color(.systemGray5))
                        .frame(width: 100, height: 16)
                }
                Spacer()
            }

            RoundedRectangle(cornerRadius: 4)
                .fill(Color(.systemGray5))
                .frame(height: 40)

            HStack {
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 80, height: 14)
                Spacer()
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 60, height: 14)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .redacted(reason: .placeholder)
    }
}

#Preview {
    DiscoveryView()
        .environmentObject(AuthService.shared)
        .environmentObject(AppState())
}
