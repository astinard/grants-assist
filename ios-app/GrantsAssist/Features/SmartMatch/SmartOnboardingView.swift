import SwiftUI

// MARK: - Smart Onboarding View

struct SmartOnboardingView: View {
    @StateObject private var viewModel = SmartOnboardingViewModel()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                // Background gradient
                LinearGradient(
                    colors: [Color.accentColor.opacity(0.1), Color(.systemBackground)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Progress Bar
                    progressBar

                    // Content
                    TabView(selection: $viewModel.currentStep) {
                        orgNameStep.tag(0)
                        zipCodeStep.tag(1)
                        sectorStep.tag(2)
                        fundingStep.tag(3)
                        samStep.tag(4)
                        resultsStep.tag(5)
                    }
                    .tabViewStyle(.page(indexDisplayMode: .never))
                    .animation(.easeInOut, value: viewModel.currentStep)

                    // Navigation Buttons
                    if viewModel.currentStep < 5 {
                        navigationButtons
                    }
                }
            }
            .navigationTitle("Find Your Grants")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    // MARK: - Progress Bar

    private var progressBar: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(Color(.systemGray5))
                    .frame(height: 4)

                Rectangle()
                    .fill(Color.accentColor)
                    .frame(width: geometry.size.width * CGFloat(viewModel.currentStep) / 5.0, height: 4)
                    .animation(.spring(), value: viewModel.currentStep)
            }
        }
        .frame(height: 4)
        .padding(.horizontal)
        .padding(.top)
    }

    // MARK: - Step 1: Organization Name

    private var orgNameStep: some View {
        VStack(spacing: 24) {
            Spacer()

            stepHeader(
                icon: "building.2",
                title: "What's your organization name?",
                subtitle: "We'll look up your EIN and verify 501(c)(3) status automatically"
            )

            VStack(spacing: 12) {
                TextField("Organization name", text: $viewModel.orgName)
                    .textFieldStyle(.roundedBorder)
                    .font(.title3)
                    .padding(.horizontal, 32)
                    .onSubmit {
                        Task { await viewModel.lookupOrganization() }
                    }

                if viewModel.isSearchingOrg {
                    ProgressView("Searching...")
                        .padding()
                }

                if let nonprofit = viewModel.foundNonprofit {
                    nonprofitCard(nonprofit)
                        .padding(.horizontal, 32)
                }

                if !viewModel.nonprofitSuggestions.isEmpty && viewModel.foundNonprofit == nil {
                    nonprofitSuggestions
                }
            }

            Spacer()
        }
    }

    private func nonprofitCard(_ nonprofit: NonprofitSearchResult) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                Text("Organization Found")
                    .fontWeight(.semibold)
            }

            Text(nonprofit.name)
                .font(.headline)

            HStack(spacing: 16) {
                Label("EIN: \(nonprofit.ein)", systemImage: "number")
                    .font(.caption)
                if nonprofit.is501c3 {
                    Label("501(c)(3)", systemImage: "checkmark.seal.fill")
                        .font(.caption)
                        .foregroundStyle(.green)
                }
            }

            if let revenue = nonprofit.totalRevenue {
                Text("Annual Revenue: $\(Int(revenue).formatted())")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color.green.opacity(0.1))
        .cornerRadius(12)
    }

    private var nonprofitSuggestions: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Did you mean:")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 32)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(viewModel.nonprofitSuggestions.prefix(5)) { nonprofit in
                        Button {
                            viewModel.selectNonprofit(nonprofit)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(nonprofit.name)
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                    .lineLimit(2)

                                if nonprofit.is501c3 {
                                    Text("501(c)(3)")
                                        .font(.caption2)
                                        .foregroundStyle(.green)
                                }
                            }
                            .padding()
                            .frame(width: 180)
                            .background(Color(.systemGray6))
                            .cornerRadius(12)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 32)
            }
        }
    }

    // MARK: - Step 2: ZIP Code

    private var zipCodeStep: some View {
        VStack(spacing: 24) {
            Spacer()

            stepHeader(
                icon: "location",
                title: "What's your ZIP code?",
                subtitle: "We'll determine rural eligibility and community need automatically"
            )

            VStack(spacing: 16) {
                TextField("ZIP code", text: $viewModel.zipCode)
                    .textFieldStyle(.roundedBorder)
                    .font(.title3)
                    .keyboardType(.numberPad)
                    .frame(width: 150)
                    .multilineTextAlignment(.center)
                    .onChange(of: viewModel.zipCode) { newValue in
                        if newValue.count == 5 {
                            Task { await viewModel.lookupZipCode() }
                        }
                    }

                if viewModel.isSearchingZip {
                    ProgressView("Looking up demographics...")
                        .padding()
                }

                if let zipData = viewModel.zipData {
                    zipDataCard(zipData)
                        .padding(.horizontal, 32)
                }
            }

            Spacer()
        }
    }

    private func zipDataCard(_ data: ZipLookupResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            if let demo = data.demographics {
                HStack {
                    Image(systemName: "mappin.circle.fill")
                        .foregroundStyle(.blue)
                    Text(demo.locationName ?? "Location")
                        .fontWeight(.semibold)
                }

                HStack(spacing: 24) {
                    if let poverty = demo.povertyRate {
                        VStack(alignment: .leading) {
                            Text("\(Int(poverty))%")
                                .font(.title2)
                                .fontWeight(.bold)
                                .foregroundStyle(poverty > 20 ? .orange : .primary)
                            Text("Poverty Rate")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    if let income = demo.medianIncome {
                        VStack(alignment: .leading) {
                            Text("$\(Int(income).formatted())")
                                .font(.title2)
                                .fontWeight(.bold)
                            Text("Median Income")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if demo.isHighNeed {
                    Label("High-Need Community", systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }

            if let rural = data.ruralStatus, rural.isRural {
                Label("Rural Area - USDA Eligible", systemImage: "leaf.fill")
                    .font(.caption)
                    .foregroundStyle(.green)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color.blue.opacity(0.1))
        .cornerRadius(12)
    }

    // MARK: - Step 3: Sector

    private var sectorStep: some View {
        VStack(spacing: 24) {
            Spacer()

            stepHeader(
                icon: "square.grid.2x2",
                title: "What sector do you work in?",
                subtitle: "This helps us find grants in your field"
            )

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                ForEach(Sector.allCases, id: \.self) { sector in
                    sectorButton(sector)
                }
            }
            .padding(.horizontal, 32)

            Spacer()
        }
    }

    private func sectorButton(_ sector: Sector) -> some View {
        Button {
            viewModel.sector = sector
        } label: {
            VStack(spacing: 8) {
                Image(systemName: sector.icon)
                    .font(.title)
                Text(sector.displayName)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
            .background(viewModel.sector == sector ? Color.accentColor : Color(.systemGray6))
            .foregroundStyle(viewModel.sector == sector ? .white : .primary)
            .cornerRadius(16)
        }
    }

    // MARK: - Step 4: Funding Range

    private var fundingStep: some View {
        VStack(spacing: 24) {
            Spacer()

            stepHeader(
                icon: "dollarsign.circle",
                title: "How much funding are you seeking?",
                subtitle: "We'll match grants in your target range"
            )

            VStack(spacing: 12) {
                ForEach(FundingRange.allCases, id: \.self) { range in
                    fundingButton(range)
                }
            }
            .padding(.horizontal, 32)

            Spacer()
        }
    }

    private func fundingButton(_ range: FundingRange) -> some View {
        Button {
            viewModel.fundingRange = range
        } label: {
            HStack {
                Text(range.displayName)
                    .fontWeight(.medium)
                Spacer()
                if viewModel.fundingRange == range {
                    Image(systemName: "checkmark.circle.fill")
                }
            }
            .padding()
            .background(viewModel.fundingRange == range ? Color.accentColor : Color(.systemGray6))
            .foregroundStyle(viewModel.fundingRange == range ? .white : .primary)
            .cornerRadius(12)
        }
    }

    // MARK: - Step 5: SAM Registration

    private var samStep: some View {
        VStack(spacing: 24) {
            Spacer()

            stepHeader(
                icon: "checkmark.shield",
                title: "Are you registered on SAM.gov?",
                subtitle: "Required for most federal grants"
            )

            VStack(spacing: 12) {
                ForEach(SAMStatus.allCases, id: \.self) { status in
                    samButton(status)
                }
            }
            .padding(.horizontal, 32)

            if viewModel.samStatus == .no {
                Text("No worries! We'll still show you grants and help you register.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            Spacer()
        }
    }

    private func samButton(_ status: SAMStatus) -> some View {
        Button {
            viewModel.samStatus = status
        } label: {
            HStack {
                Text(status.displayName)
                    .fontWeight(.medium)
                Spacer()
                if viewModel.samStatus == status {
                    Image(systemName: "checkmark.circle.fill")
                }
            }
            .padding()
            .background(viewModel.samStatus == status ? Color.accentColor : Color(.systemGray6))
            .foregroundStyle(viewModel.samStatus == status ? .white : .primary)
            .cornerRadius(12)
        }
    }

    // MARK: - Step 6: Results

    private var resultsStep: some View {
        VStack(spacing: 20) {
            if viewModel.isLoadingMatches {
                Spacer()
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.5)
                    Text("Finding your best matches...")
                        .font(.headline)
                    Text("Analyzing 900+ grants against your profile")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            } else if let response = viewModel.matchResponse {
                resultsContent(response)
            } else if let error = viewModel.matchError {
                errorView(error)
            }
        }
    }

    private func resultsContent(_ response: SmartMatchResponse) -> some View {
        ScrollView {
            VStack(spacing: 20) {
                // Header
                VStack(spacing: 8) {
                    Image(systemName: "sparkles")
                        .font(.largeTitle)
                        .foregroundStyle(.yellow)

                    Text("Your Top Matches")
                        .font(.title2)
                        .fontWeight(.bold)

                    Text("Based on your profile")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top)

                // Auto-detected badges
                if let auto = response.autoDetected {
                    autoDetectedBadges(auto)
                }

                // Match cards
                ForEach(Array(response.matches.enumerated()), id: \.element.id) { index, match in
                    matchCard(match, rank: index + 1)
                }

                // Done button
                Button {
                    dismiss()
                } label: {
                    Text("Done")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.accentColor)
                        .cornerRadius(12)
                }
                .padding(.horizontal)
                .padding(.bottom, 32)
            }
            .padding(.horizontal)
        }
    }

    private func autoDetectedBadges(_ auto: AutoDetectedData) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                if auto.nonprofit?.is501c3 == true {
                    badge("501(c)(3) Verified", icon: "checkmark.seal.fill", color: .green)
                }
                if auto.rural?.isRural == true {
                    badge("Rural Eligible", icon: "leaf.fill", color: .green)
                }
                if auto.demographics?.isHighNeed == true {
                    badge("High-Need Area", icon: "exclamationmark.triangle.fill", color: .orange)
                }
            }
        }
    }

    private func badge(_ text: String, icon: String, color: Color) -> some View {
        HStack(spacing: 4) {
            Image(systemName: icon)
            Text(text)
        }
        .font(.caption)
        .fontWeight(.medium)
        .foregroundStyle(color)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(color.opacity(0.15))
        .cornerRadius(20)
    }

    private func matchCard(_ match: SmartMatchResult, rank: Int) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header with rank and score
            HStack {
                // Rank medal
                Text(rankMedal(rank))
                    .font(.title2)

                VStack(alignment: .leading, spacing: 2) {
                    Text(match.programName)
                        .font(.headline)
                        .lineLimit(2)

                    Text(match.agency)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                // Match score
                VStack(spacing: 2) {
                    Text("\(match.matchScore)%")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundStyle(matchColor(match.matchLevelEnum))

                    Text("match")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            // Why this matches
            if let reason = match.reasons.first {
                Text(reason.explanation)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Divider()

            // Details
            HStack(spacing: 16) {
                Label(match.awardText, systemImage: "dollarsign.circle")
                    .font(.caption)
                Spacer()
                Label(match.deadlineText, systemImage: "calendar")
                    .font(.caption)
            }
            .foregroundStyle(.secondary)

            // Missing requirements
            if !match.missingRequirements.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "exclamationmark.circle")
                        .foregroundStyle(.orange)
                    Text(match.missingRequirements.first ?? "")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 5, x: 0, y: 2)
    }

    private func rankMedal(_ rank: Int) -> String {
        switch rank {
        case 1: return "🥇"
        case 2: return "🥈"
        case 3: return "🥉"
        default: return "\(rank)."
        }
    }

    private func matchColor(_ level: SmartMatchResult.MatchLevel) -> Color {
        switch level {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .poor: return .red
        }
    }

    private func errorView(_ error: String) -> some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundStyle(.orange)
            Text("Couldn't load matches")
                .font(.headline)
            Text(error)
                .font(.caption)
                .foregroundStyle(.secondary)
            Button("Try Again") {
                Task { await viewModel.findMatches() }
            }
            .buttonStyle(.bordered)
            Spacer()
        }
    }

    // MARK: - Step Header

    private func stepHeader(icon: String, title: String, subtitle: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(.accentColor)

            Text(title)
                .font(.title2)
                .fontWeight(.bold)
                .multilineTextAlignment(.center)

            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.horizontal, 32)
    }

    // MARK: - Navigation Buttons

    private var navigationButtons: some View {
        HStack(spacing: 16) {
            if viewModel.currentStep > 0 {
                Button {
                    withAnimation { viewModel.previousStep() }
                } label: {
                    HStack {
                        Image(systemName: "chevron.left")
                        Text("Back")
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
            }

            Button {
                if viewModel.currentStep == 4 {
                    Task { await viewModel.findMatches() }
                }
                withAnimation { viewModel.nextStep() }
            } label: {
                HStack {
                    Text(viewModel.currentStep == 4 ? "Find Matches" : "Next")
                    Image(systemName: viewModel.currentStep == 4 ? "sparkles" : "chevron.right")
                }
                .fontWeight(.semibold)
                .foregroundStyle(.white)
                .padding()
                .frame(maxWidth: .infinity)
                .background(viewModel.canProceed ? Color.accentColor : Color.gray)
                .cornerRadius(12)
            }
            .disabled(!viewModel.canProceed)
        }
        .padding()
    }
}

// MARK: - Supporting Types

enum Sector: String, CaseIterable {
    case healthcare, education, agriculture, smallBusiness, housing, technology, other

    var displayName: String {
        switch self {
        case .healthcare: return "Healthcare"
        case .education: return "Education"
        case .agriculture: return "Agriculture"
        case .smallBusiness: return "Small Business"
        case .housing: return "Housing"
        case .technology: return "Technology"
        case .other: return "Other"
        }
    }

    var icon: String {
        switch self {
        case .healthcare: return "cross.case"
        case .education: return "graduationcap"
        case .agriculture: return "leaf"
        case .smallBusiness: return "building.2"
        case .housing: return "house"
        case .technology: return "cpu"
        case .other: return "square.grid.2x2"
        }
    }

    var apiValue: String {
        switch self {
        case .healthcare: return "healthcare"
        case .education: return "education"
        case .agriculture: return "agriculture"
        case .smallBusiness: return "small_business"
        case .housing: return "housing"
        case .technology: return "technology"
        case .other: return "nonprofit"
        }
    }
}

enum FundingRange: String, CaseIterable {
    case under50k, range50to250k, range250kto1m, over1m

    var displayName: String {
        switch self {
        case .under50k: return "Under $50,000"
        case .range50to250k: return "$50,000 - $250,000"
        case .range250kto1m: return "$250,000 - $1 million"
        case .over1m: return "Over $1 million"
        }
    }

    var minValue: Double? {
        switch self {
        case .under50k: return nil
        case .range50to250k: return 50_000
        case .range250kto1m: return 250_000
        case .over1m: return 1_000_000
        }
    }

    var maxValue: Double? {
        switch self {
        case .under50k: return 50_000
        case .range50to250k: return 250_000
        case .range250kto1m: return 1_000_000
        case .over1m: return nil
        }
    }
}

enum SAMStatus: String, CaseIterable {
    case yes, no, dontKnow

    var displayName: String {
        switch self {
        case .yes: return "Yes"
        case .no: return "No"
        case .dontKnow: return "Don't know"
        }
    }

    var boolValue: Bool? {
        switch self {
        case .yes: return true
        case .no: return false
        case .dontKnow: return nil
        }
    }
}

#Preview {
    SmartOnboardingView()
}
