import AppKit
import SwiftUI

let reportURL = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/WeeklyReport/report.md")

final class Model: ObservableObject {
    @Published var text = ""
    @Published var busy = false
    @Published var failed = false

    func load() {
        text = (try? String(contentsOf: reportURL, encoding: .utf8)) ?? "还没有周报，点右上角刷新按钮生成。"
    }

    func refresh() {
        guard !busy, let script = Bundle.main.path(forResource: "generate", ofType: "py") else { return }
        busy = true
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [script]
        process.terminationHandler = { p in
            DispatchQueue.main.async {
                self.busy = false
                self.failed = p.terminationStatus != 0
                self.load()
            }
        }
        do { try process.run() } catch { busy = false; failed = true }
    }

    func copy() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }
}

struct CardView: View {
    @ObservedObject var model: Model

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 12) {
                Text("本周周报").font(.headline)
                if model.failed {
                    Text("生成失败").font(.caption).foregroundStyle(.red)
                }
                Spacer()
                if model.busy {
                    ProgressView().controlSize(.small)
                } else {
                    Button(action: model.refresh) { Image(systemName: "arrow.clockwise") }.help("重新生成")
                }
                Button(action: model.copy) { Image(systemName: "doc.on.doc") }.help("复制 Markdown")
                Button(action: { NSApp.terminate(nil) }) { Image(systemName: "xmark") }.help("退出")
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 5) {
                    let lines = model.text.components(separatedBy: "\n")
                    ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                        row(line)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
            }
        }
        .font(.system(size: 13))
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    @ViewBuilder
    func row(_ line: String) -> some View {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        let indent = CGFloat(line.prefix { $0 == " " }.count) * 6
        if trimmed.hasPrefix("# ") {
            Text(inline(String(trimmed.dropFirst(2)))).font(.title3.bold())
        } else if trimmed.hasPrefix("## ") {
            Text(inline(String(trimmed.dropFirst(3)))).font(.system(size: 15, weight: .bold)).padding(.top, 10)
        } else if trimmed.hasPrefix("- ") {
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text("•").foregroundStyle(.secondary)
                Text(inline(String(trimmed.dropFirst(2))))
            }
            .padding(.leading, indent)
        } else if !trimmed.isEmpty {
            Text(inline(trimmed))
        }
    }

    func inline(_ s: String) -> AttributedString {
        (try? AttributedString(markdown: s, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
            ?? AttributedString(s)
    }
}

// 无边框窗口默认不能成为 key window，按钮点击会不稳定
final class CardWindow: NSWindow {
    override var canBecomeKey: Bool { true }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    let model = Model()
    var window: CardWindow!

    func applicationDidFinishLaunching(_ notification: Notification) {
        let screen = NSScreen.main!.visibleFrame
        let size = NSSize(width: 400, height: 600)
        window = CardWindow(
            contentRect: NSRect(x: screen.maxX - size.width - 24, y: screen.maxY - size.height - 24,
                                width: size.width, height: size.height),
            styleMask: [.borderless, .resizable], backing: .buffered, defer: false)
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true
        window.isMovableByWindowBackground = true
        // 贴在桌面图标之上、所有普通窗口之下
        window.level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.desktopIconWindow)) + 1)
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        window.contentView = NSHostingView(rootView: CardView(model: model))
        window.setFrameAutosaveName("WeeklyReportCard")
        window.orderFront(nil)

        model.load()
        // 定时任务更新了文件后同步到卡片
        Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { _ in
            if !self.model.busy { self.model.load() }
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
