import SwiftUI

struct DetailView: View {
    let title: String
    @State private var favourite = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title).font(.title).accessibilityIdentifier("detailTitle")
            Text("This is the detail screen for the item you tapped.")
                .accessibilityIdentifier("detailBody")
            Button(favourite ? "Unmark favourite" : "Mark favourite") { favourite.toggle() }
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("favourite")
            Text(favourite ? "A favourite" : "Not a favourite")
                .accessibilityIdentifier("favouriteState")
            Spacer()
        }
        .padding(24)
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
