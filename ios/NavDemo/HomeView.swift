import SwiftUI

struct HomeView: View {
    @State private var count = 0
    @State private var notifications = false
    @State private var showDialog = false
    @State private var dialogResult = ""

    var body: some View {
        List {
            Section {
                HStack {
                    Button("Increment") { count += 1 }
                        .buttonStyle(.bordered)
                        .accessibilityIdentifier("increment")
                    Text("\(count)")
                        .font(.title3)
                        .accessibilityIdentifier("count")
                        .accessibilityLabel("Count")
                        .accessibilityValue("\(count)")
                    Spacer()
                    Button("Show dialog") { showDialog = true }
                        .buttonStyle(.bordered)
                        .accessibilityIdentifier("showDialog")
                }
                Toggle("Notifications", isOn: $notifications)
                    .accessibilityIdentifier("notifications")
                if !dialogResult.isEmpty {
                    Text(dialogResult).foregroundStyle(.secondary).accessibilityIdentifier("dialogResult")
                }
            }
            Section("Items") {
                ForEach(Items.all, id: \.self) { item in
                    NavigationLink(item) { DetailView(title: item) }
                        .accessibilityIdentifier("item-\(item.split(separator: " ").last ?? "")")
                }
            }
        }
        .alert("A dialog", isPresented: $showDialog) {
            Button("OK") { dialogResult = "Dialog: OK" }
            Button("Cancel", role: .cancel) { dialogResult = "Dialog: Cancel" }
        } message: {
            Text("Native dialogs show up in the tree too.")
        }
    }
}
