import SwiftUI

@main
struct NavDemoApp: App {
    @StateObject private var session = Session()

    var body: some Scene {
        WindowGroup {
            if session.user == nil {
                LoginView().environmentObject(session)
            } else {
                MainTabView().environmentObject(session)
            }
        }
    }
}
