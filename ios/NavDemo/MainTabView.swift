import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            NavigationStack { HomeView().navigationTitle("Home") }
                .tabItem { Label("Home", systemImage: "house") }
            NavigationStack { WebTabView().navigationTitle("Web") }
                .tabItem { Label("Web", systemImage: "globe") }
            NavigationStack { SearchView().navigationTitle("Search") }
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
            NavigationStack { ProfileView().navigationTitle("Profile") }
                .tabItem { Label("Profile", systemImage: "person") }
        }
    }
}
