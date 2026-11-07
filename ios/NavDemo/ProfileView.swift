import SwiftUI

struct ProfileView: View {
    @EnvironmentObject var session: Session
    @State private var confirm = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(session.user ?? "nobody").font(.title2).accessibilityIdentifier("profileName")
            if let since = session.since {
                Text("Signed in \(since.formatted(date: .omitted, time: .shortened))")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("profileSince")
            }
            Button("Log out") { confirm = true }
                .buttonStyle(.bordered)
                .padding(.top, 16)
                .accessibilityIdentifier("logout")
            Spacer()
        }
        .padding(24)
        .confirmationDialog("Log out?", isPresented: $confirm, titleVisibility: .visible) {
            Button("Log out", role: .destructive) { session.signOut() }
            Button("Cancel", role: .cancel) {}
        }
    }
}
