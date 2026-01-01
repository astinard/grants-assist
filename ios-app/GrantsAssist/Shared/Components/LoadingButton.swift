import SwiftUI

struct LoadingButton: View {
    let title: String
    let isLoading: Bool
    let action: () -> Void

    var style: Style = .primary

    enum Style {
        case primary
        case secondary
        case destructive
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isLoading {
                    ProgressView()
                        .tint(foregroundColor)
                }

                Text(title)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 50)
            .background(backgroundColor)
            .foregroundStyle(foregroundColor)
            .cornerRadius(12)
        }
        .disabled(isLoading)
    }

    private var backgroundColor: Color {
        switch style {
        case .primary: return .accentColor
        case .secondary: return Color(.systemGray5)
        case .destructive: return .red
        }
    }

    private var foregroundColor: Color {
        switch style {
        case .primary, .destructive: return .white
        case .secondary: return .primary
        }
    }
}

extension LoadingButton {
    func buttonStyle(_ style: Style) -> LoadingButton {
        var button = self
        button.style = style
        return button
    }
}

#Preview {
    VStack(spacing: 16) {
        LoadingButton(title: "Primary", isLoading: false) {}
        LoadingButton(title: "Loading", isLoading: true) {}
        LoadingButton(title: "Secondary", isLoading: false) {}.buttonStyle(.secondary)
        LoadingButton(title: "Destructive", isLoading: false) {}.buttonStyle(.destructive)
    }
    .padding()
}
