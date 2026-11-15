import SwiftUI

/// A native twin of shared/web/index.html: the same elements, texts, order and accessibility
/// identifiers (the HTML ids), laid out the same way, so one navigation script runs on both and
/// a tool's cost on native content can be set against its cost on the same page in a WebView.
struct NativePageView: View {
    @State private var greeting = ""
    @State private var name = ""
    @State private var colour = "Red"
    @State private var result = ""
    @State private var late = "Loading…"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("NavDemo Web").font(.system(size: 22, weight: .bold))
                    .accessibilityAddTraits(.isHeader).accessibilityIdentifier("title")
                Text("This page is served from the app bundle, so the WebView works offline.")
                    .padding(.top, 16)
                heading("Actions")
                Button("Say hello") { greeting = "Hello from the web" }
                    .buttonStyle(.borderedProminent).accessibilityIdentifier("hello").padding(.top, 8)
                Text(greeting).fontWeight(.semibold).frame(minHeight: 20).padding(.top, 16)
                    .accessibilityIdentifier("greeting")

                heading("Form")
                Text("Your name").padding(.top, 8)
                TextField("Type a name", text: $name)
                    .textFieldStyle(.roundedBorder).frame(maxWidth: 215)
                    .autocorrectionDisabled().textInputAutocapitalization(.never)
                    .accessibilityLabel("Your name").accessibilityIdentifier("name")
                    .onSubmit(send)
                Text("Favourite colour").padding(.top, 8)
                Picker("Favourite colour", selection: $colour) {
                    ForEach(["Red", "Green", "Blue"], id: \.self) { Text($0) }
                }
                .pickerStyle(.menu).accessibilityIdentifier("color")
                Button("Send", action: send)
                    .buttonStyle(.borderedProminent).accessibilityIdentifier("send").padding(.top, 4)
                Text(result).fontWeight(.semibold).frame(minHeight: 20).padding(.top, 16)
                    .accessibilityIdentifier("result")

                heading("Navigation")
                NavigationLink("Second page") { NativePage2View() }
                    .accessibilityIdentifier("second").padding(.top, 16)

                heading("Slow content")
                Text(late).fontWeight(.semibold).padding(.top, 16).accessibilityIdentifier("late")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
        }
        .task {
            try? await Task.sleep(for: .milliseconds(1500))
            late = "Loaded late"
        }
    }

    private func heading(_ text: String) -> some View {
        Text(text).font(.system(size: 18, weight: .bold)).padding(.top, 24).accessibilityAddTraits(.isHeader)
    }

    private func send() { result = "Sent: \(name), \(colour)" }
}

/// The twin of shared/web/page2.html.
struct NativePage2View: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Second page").font(.system(size: 32, weight: .bold))
                    .accessibilityAddTraits(.isHeader).accessibilityIdentifier("title")
                Button("Back to start") { dismiss() }.accessibilityIdentifier("back").padding(.vertical, 16)
                ForEach(1...40, id: \.self) { i in
                    Text("• Web row \(i)").padding(.vertical, 10).padding(.leading, 24)
                        .accessibilityLabel("Web row \(i)").accessibilityIdentifier("row-\(i)")
                }
                Text("You reached the bottom.").padding(.top, 16).accessibilityIdentifier("bottom")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
        }
        .navigationTitle("Second page")
        .navigationBarTitleDisplayMode(.inline)
    }
}
