import AppKit
import SwiftUI

struct Widget {
    let id: String      // 对应 widgets/<id>.py 和数据目录下的 <id>.md
    let title: String
    let icon: String    // 分块标题前的图标
    var action: Action? = nil

    // 标签页上的额外按钮：确认后运行 widgets/<script>.py
    struct Action {
        let script: String
        let symbol: String
        let help: String
        let confirm: String
    }
}

let allWidgets = [
    Widget(id: "weekly", title: "周报", icon: "shippingbox.fill"),
    Widget(id: "standup", title: "站会", icon: "calendar"),
    Widget(id: "repos", title: "仓库", icon: "folder.fill"),
    Widget(id: "usage", title: "用量", icon: "chart.bar.fill"),
    Widget(id: "todo", title: "待办", icon: "checklist"),
    Widget(id: "releases", title: "发布", icon: "shippingbox.fill"),
    Widget(id: "hours", title: "工时", icon: "clock.fill", action: .init(
        script: "hours_log", symbol: "checkmark.circle", help: "登记到 ONES",
        confirm: "把卡片上待登记的工时写入 ONES？")),
]

let dataDir = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/WeeklyReport")

// 配置里的 tabs 决定显示哪些标签及顺序，没配就全部显示
let widgets: [Widget] = {
    guard let data = try? Data(contentsOf: dataDir.appendingPathComponent("config.json")),
          let config = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let tabs = config["tabs"] as? [String] else { return allWidgets }
    let chosen = tabs.compactMap { id in allWidgets.first { $0.id == id } }
    return chosen.isEmpty ? allWidgets : chosen
}()

final class Model: ObservableObject {
    @Published var texts: [String: String] = [:]
    @Published var busy: Set<String> = []
    @Published var failed: Set<String> = []

    func load() {
        for widget in widgets {
            texts[widget.id] = (try? String(
                contentsOf: dataDir.appendingPathComponent(widget.id + ".md"), encoding: .utf8))
                ?? "还没有内容，点右上角刷新按钮生成。"
        }
    }

    /// 运行 widgets/<script>.py 并重新加载；script 省略时就是重新生成该标签页
    func refresh(_ id: String, script: String? = nil) {
        guard !busy.contains(id), let resources = Bundle.main.resourcePath else { return }
        busy.insert(id)
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [resources + "/widgets/run.py", script ?? id]
        process.terminationHandler = { p in
            DispatchQueue.main.async {
                self.busy.remove(id)
                if p.terminationStatus == 0 { self.failed.remove(id) } else { self.failed.insert(id) }
                self.load()
            }
        }
        do { try process.run() } catch { busy.remove(id); failed.insert(id) }
    }

    func copy(_ id: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(texts[id] ?? "", forType: .string)
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
    @AppStorage("tab") private var tab = widgets[0].id

    var body: some View {
        let widget = widgets.first { $0.id == tab } ?? widgets[0]
        let report = parse(model.texts[widget.id] ?? "")
        let busy = model.busy.contains(widget.id)
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 8) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(report.title.isEmpty ? widget.title : report.title)
                        .font(.system(size: 16, weight: .semibold))
                    if model.failed.contains(widget.id) {
                        Text("生成失败，详见日志").font(.caption).foregroundStyle(.red)
                    } else if busy {
                        Text("正在生成…").font(.caption).foregroundStyle(.secondary)
                    } else if !report.updated.isEmpty {
                        Text(report.updated).font(.caption).foregroundStyle(.secondary)
                    }
                }
                Spacer()
                if busy {
                    ProgressView().controlSize(.small).frame(width: 26, height: 26)
                } else {
                    if let action = widget.action {
                        IconButton(symbol: action.symbol, help: action.help) {
                            let alert = NSAlert()
                            alert.messageText = action.confirm
                            alert.addButton(withTitle: "确定")
                            alert.addButton(withTitle: "取消")
                            if alert.runModal() == .alertFirstButtonReturn {
                                model.refresh(widget.id, script: action.script)
                            }
                        }
                    }
                    IconButton(symbol: "arrow.clockwise", help: "重新生成") { model.refresh(widget.id) }
                }
                IconButton(symbol: copied ? "checkmark" : "doc.on.doc", help: "复制 Markdown") {
                    model.copy(widget.id)
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                }
                IconButton(symbol: "xmark", help: "退出") { NSApp.terminate(nil) }
            }
            .padding(.horizontal, 18)
            .padding(.top, 16)
            .padding(.bottom, 10)

            ScrollView(.horizontal) {
              HStack(spacing: 6) {
                ForEach(widgets, id: \.id) { item in
                    Button(action: { tab = item.id }) {
                        Text(item.title)
                            .font(.system(size: 12, weight: .medium))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 4)
                            .background(
                                item.id == tab ? Color.accentColor.opacity(0.2) : Color.primary.opacity(0.06),
                                in: Capsule())
                            .foregroundStyle(item.id == tab ? Color.accentColor : Color.secondary)
                            .contentShape(Capsule())
                    }
                    .buttonStyle(.plain)
                }
              }
              .padding(.horizontal, 18)
            }
            .scrollIndicators(.never)
            .padding(.bottom, 12)

            ScrollView {
                VStack(spacing: 10) {
                    ForEach(report.sections) { section in
                        sectionCard(section, icon: widget.icon)
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

    func sectionCard(_ section: ReportSection, icon: String) -> some View {
        let isOverview = section.title.contains("概览")
        return VStack(alignment: .leading, spacing: 6) {
            if !section.title.isEmpty {
                Label {
                    Text(section.title).font(.system(size: 14, weight: .semibold))
                } icon: {
                    Image(systemName: isOverview ? "sparkles" : icon)
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
            Label {
                Text(inline(String(trimmed.dropFirst(3))))
            } icon: {
                Image(systemName: "arrow.triangle.branch")
            }
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
            self.model.load()
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
