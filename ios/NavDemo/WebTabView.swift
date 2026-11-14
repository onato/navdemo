import SwiftUI
import WebKit

/// The Web tab's page is inspectable in Debug builds; the Plain web tab's never is, so tools can be
/// compared on the same page read both ways, and in one app that has both kinds of WebView.
struct WebTabView: View {
    @StateObject private var model: WebModel

    init(inspectable: Bool) { _model = StateObject(wrappedValue: WebModel(inspectable: inspectable)) }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button("Reload") { model.reload() }
                    .buttonStyle(.bordered)
                    .accessibilityIdentifier("reload")
                Text(model.status).foregroundStyle(.secondary).accessibilityIdentifier("webStatus")
                Spacer()
            }
            .padding(8)
            if model.loading {
                ProgressView(value: model.progress).accessibilityIdentifier("webProgress")
            }
            WebView(model: model)
        }
    }
}

final class WebModel: NSObject, ObservableObject, WKNavigationDelegate {
    @Published var status = "idle"
    @Published var loading = false
    @Published var progress: Double = 0
    let webView: WKWebView
    private var observation: NSKeyValueObservation?

    init(inspectable: Bool) {
        let config = WKWebViewConfiguration()
        webView = WKWebView(frame: .zero, configuration: config)
        #if DEBUG
        // Lets Safari's Web Inspector and webinspectord clients read the page's DOM.
        webView.isInspectable = inspectable
        #endif
        super.init()
        webView.navigationDelegate = self
        observation = webView.observe(\.estimatedProgress) { [weak self] wv, _ in
            self?.progress = wv.estimatedProgress
        }
        load()
    }

    func load() {
        if let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "web") {
            webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        } else {
            status = "missing web/index.html"
        }
    }

    func reload() { webView.reload() }

    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        status = "loading"; loading = true
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        status = "loaded"; loading = false
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        status = "failed"; loading = false
    }
}

struct WebView: UIViewRepresentable {
    let model: WebModel
    func makeUIView(context: Context) -> WKWebView { model.webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
