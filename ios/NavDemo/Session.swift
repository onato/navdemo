import Foundation

final class Session: ObservableObject {
    @Published private(set) var user: String?
    @Published private(set) var since: Date?

    init() {
        user = UserDefaults.standard.string(forKey: "user")
        since = UserDefaults.standard.object(forKey: "since") as? Date
    }

    /// Any username; the password is "demo". Returns an error message, or nil on success.
    func signIn(user: String, password: String) -> String? {
        let name = user.trimmingCharacters(in: .whitespaces)
        if name.isEmpty { return "Enter a username" }
        if password != "demo" { return "Wrong password" }
        UserDefaults.standard.set(name, forKey: "user")
        UserDefaults.standard.set(Date(), forKey: "since")
        self.user = name
        self.since = Date()
        return nil
    }

    func signOut() {
        UserDefaults.standard.removeObject(forKey: "user")
        UserDefaults.standard.removeObject(forKey: "since")
        user = nil
        since = nil
    }
}

enum Items {
    static let all: [String] = (1...30).map { "Item \($0)" }
}
