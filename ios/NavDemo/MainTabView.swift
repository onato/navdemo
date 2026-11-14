import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            NavigationStack { HomeView().navigationTitle("Home") }
                .tabItem { Label("Home", systemImage: "house") }
            NavigationStack { WebTabView(inspectable: true).navigationTitle("Web") }
                .tabItem { Label("Web", systemImage: "globe") }
            NavigationStack { WebTabView(inspectable: false).navigationTitle("Plain web") }
                .tabItem { Label("Plain web", systemImage: "network") }
            NavigationStack { SearchView().navigationTitle("Search") }
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
            NavigationStack { ProfileView().navigationTitle("Profile") }
                .tabItem { Label("Profile", systemImage: "person") }
        }
    }
}
