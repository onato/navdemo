import SwiftUI

struct LoginView: View {
    @EnvironmentObject var session: Session
    @State private var username = ""
    @State private var password = ""
    @State private var error: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Sign in to NavDemo")
                .font(.title)
                .accessibilityIdentifier("loginTitle")
            TextField("Username", text: $username)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier("username")
            SecureField("Password", text: $password)
                .textFieldStyle(.roundedBorder)
                .submitLabel(.done)
                .onSubmit(attempt)
                .accessibilityIdentifier("password")
            Button("Sign in", action: attempt)
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("signIn")
            if let error {
                Text(error).foregroundStyle(.red).accessibilityIdentifier("loginError")
            }
            Text("Any username, password is demo")
                .font(.footnote).foregroundStyle(.secondary)
                .accessibilityIdentifier("hint")
            Spacer()
        }
        .padding(24)
    }

    private func attempt() {
        error = session.signIn(user: username, password: password)
    }
}
