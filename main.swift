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

struct ReportSection: Identifiable {
    let id: Int
    let title: String
    var lines: [String] = []
}

struct IconButton: View {
    let symbol: String
    let help: String
    let action: () -> Void
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 12, weight: .medium))
                .frame(width: 26, height: 26)
                .background(Color.primary.opacity(hovering ? 0.14 : 0.06), in: Circle())
                .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(.secondary)
        .onHover { hovering = $0 }
        .help(help)
    }
}

struct CardView: View {
    @ObservedObject var model: Model
    @State private var copied = false

    var body: some View {
        let report = parse(model.text)
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 8) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(report.title.isEmpty ? "本周周报" : report.title)
                        .font(.system(size: 16, weight: .semibold))
                    if model.failed {
                        Text("生成失败，详见日志").font(.caption).foregroundStyle(.red)
                    } else if model.busy {
                        Text("正在生成…").font(.caption).foregroundStyle(.secondary)
                    } else if !report.updated.isEmpty {
                        Text(report.updated).font(.caption).foregroundStyle(.secondary)
                    }
                }
                Spacer()
                if model.busy {
                    ProgressView().controlSize(.small).frame(width: 26, height: 26)
                } else {
                    IconButton(symbol: "arrow.clockwise", help: "重新生成", action: model.refresh)
                }
                IconButton(symbol: copied ? "checkmark" : "doc.on.doc", help: "复制 Markdown") {
                    model.copy()
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                }
                IconButton(symbol: "xmark", help: "退出") { NSApp.terminate(nil) }
            }
            .padding(.horizontal, 18)
            .padding(.top, 16)
            .padding(.bottom, 12)

            ScrollView {
                VStack(spacing: 10) {
                    ForEach(report.sections) { section in
                        sectionCard(section)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
            }
            .scrollIndicators(.never)
        }
        .font(.system(size: 13))
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 22, style: .continuous).strokeBorder(Color.primary.opacity(0.1)))
    }

    func parse(_ text: String) -> (title: String, updated: String, sections: [ReportSection]) {
        var title = "", updated = ""
        var sections: [ReportSection] = []
        for line in text.components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("# ") {
                title = String(trimmed.dropFirst(2))
            } else if trimmed.hasPrefix("## ") {
                sections.append(ReportSection(id: sections.count, title: String(trimmed.dropFirst(3))))
            } else if trimmed.hasPrefix("更新于"), sections.isEmpty {
                updated = trimmed
            } else if !trimmed.isEmpty {
                if sections.isEmpty { sections.append(ReportSection(id: 0, title: "")) }
                sections[sections.count - 1].lines.append(line)
            }
        }
        return (title, updated, sections)
    }

    func sectionCard(_ section: ReportSection) -> some View {
        let isOverview = section.title.contains("概览")
        return VStack(alignment: .leading, spacing: 6) {
            if !section.title.isEmpty {
                Label {
                    Text(section.title).font(.system(size: 14, weight: .semibold))
                } icon: {
                    Image(systemName: isOverview ? "sparkles" : "shippingbox.fill")
                        .font(.system(size: 12))
                        .foregroundStyle(isOverview ? Color.accentColor : Color.secondary)
                }
                .padding(.bottom, 2)
            }
            ForEach(Array(section.lines.enumerated()), id: \.offset) { _, line in
                row(line)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(
            isOverview ? Color.accentColor.opacity(0.1) : Color.primary.opacity(0.05),
            in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    @ViewBuilder
    func row(_ line: String) -> some View {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        let nested = line.hasPrefix(" ")
        if trimmed.hasPrefix("分支：") || trimmed.hasPrefix("分支:") {
            Label(String(trimmed.dropFirst(3)), systemImage: "arrow.triangle.branch")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
        } else if trimmed.count > 4, trimmed.hasPrefix("**"), trimmed.hasSuffix("**") {
            // 独占一行的加粗是分组名（新功能 / 修复 / 其他）
            let name = String(trimmed.dropFirst(2).dropLast(2))
            let color: Color = name.contains("新功能") ? .green : name.contains("修复") ? .orange : .gray
            Text(name)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(color)
                .padding(.horizontal, 8)
                .padding(.vertical, 2)
                .background(color.opacity(0.15), in: Capsule())
                .padding(.top, 6)
        } else if trimmed.hasPrefix("- ") {
            HStack(alignment: .firstTextBaseline, spacing: 7) {
                Text(nested ? "–" : "•").foregroundStyle(.tertiary)
                Text(inline(String(trimmed.dropFirst(2))))
                    .lineSpacing(2.5)
                    .foregroundStyle(nested ? .secondary : .primary)
            }
            .padding(.leading, nested ? 14 : 0)
        } else {
            Text(inline(trimmed)).lineSpacing(2.5)
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
