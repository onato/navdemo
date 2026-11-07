import SwiftUI

struct SearchView: View {
    @State private var query = ""

    private var hits: [String] {
        let q = query.trimmingCharacters(in: .whitespaces)
        return q.isEmpty ? [] : Items.all.filter { $0.localizedCaseInsensitiveContains(q) }
    }

    var body: some View {
        VStack(alignment: .leading) {
            TextField("Search items", text: $query)
                .textFieldStyle(.roundedBorder)
                .autocorrectionDisabled()
                .submitLabel(.search)
                .accessibilityIdentifier("searchField")
                .padding(.horizontal)
            if !query.isEmpty && hits.isEmpty {
                Text("No results").foregroundStyle(.secondary)
                    .accessibilityIdentifier("noResults")
                    .padding(.horizontal)
            }
            List(hits, id: \.self) { item in
                NavigationLink(item) { DetailView(title: item) }
            }
            .listStyle(.plain)
        }
    }
}
