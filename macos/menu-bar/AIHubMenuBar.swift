import AppKit
import Foundation

struct HubComponent: Decodable {
    let status: String
    let message: String?
}

struct HubStatus: Decodable {
    let status: String
    let checked_at: String?
    let components: [String: HubComponent]?
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let menu = NSMenu()
    private let stateItem = NSMenuItem(title: "AI Docs Hub: проверка...", action: nil, keyEquivalent: "")
    private let updatedItem = NSMenuItem(title: "Обновляется каждые 5 секунд", action: nil, keyEquivalent: "")
    private var timer: Timer?
    private var isRefreshing = false
    private let statusURL = URL(string: "http://localhost:4321/status/")!
    private let docsURL = URL(string: "http://localhost:4321/")!
    private lazy var hubRoot: String = {
        if let value = ProcessInfo.processInfo.environment["AI_DOCS_HUB_ROOT"], !value.isEmpty {
            return value
        }
        let fileManager = FileManager.default
        let starts = [
            Bundle.main.bundleURL.deletingLastPathComponent(),
            URL(fileURLWithPath: fileManager.currentDirectoryPath)
        ]
        for start in starts {
            var current = start.standardizedFileURL
            for _ in 0..<8 {
                let marker = current
                    .appendingPathComponent("scripts")
                    .appendingPathComponent("hub-status")
                    .path
                if fileManager.isExecutableFile(atPath: marker) {
                    return current.path
                }
                let next = current.deletingLastPathComponent()
                if next.path == current.path {
                    break
                }
                current = next
            }
        }
        return fileManager.currentDirectoryPath
    }()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        configureMenu()
        configureButton(title: "xAI")
        
        timer = Timer.scheduledTimer(
            timeInterval: 5,
            target: self,
            selector: #selector(refreshStatus(_:)),
            userInfo: nil,
            repeats: true
        )
        
        // Initial refresh with small delay to ensure app is ready
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            self.refreshStatus(nil)
        }
    }

    private func configureButton(title: String) {
        if let button = statusItem.button {
            button.title = title
            button.toolTip = "AI Docs Hub"
            button.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        }
    }

    private func configureMenu() {
        stateItem.isEnabled = false
        updatedItem.isEnabled = false

        menu.addItem(stateItem)
        menu.addItem(updatedItem)
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Открыть статус", action: #selector(openStatus), keyEquivalent: "s"))
        menu.addItem(NSMenuItem(title: "Открыть документацию", action: #selector(openDocs), keyEquivalent: "d"))
        menu.addItem(NSMenuItem(title: "Обновить состояние", action: #selector(refreshStatus(_:)), keyEquivalent: "r"))
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Выход", action: #selector(quit), keyEquivalent: "q"))

        for item in menu.items where item.action != nil {
            item.target = self
        }
        statusItem.menu = menu
    }

    @objc private func openStatus() {
        NSWorkspace.shared.open(statusURL)
    }

    @objc private func openDocs() {
        NSWorkspace.shared.open(docsURL)
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }

    @objc private func refreshStatus(_ sender: Any?) {
        if isRefreshing {
            return
        }
        isRefreshing = true
        readStatus { [weak self] status in
            DispatchQueue.main.async {
                self?.isRefreshing = false
                self?.apply(status: status)
            }
        }
    }

    private func readStatus(completion: @escaping (HubStatus?) -> Void) {
        DispatchQueue.global(qos: .utility).async {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: self.hubRoot + "/scripts/hub-status")
            process.currentDirectoryURL = URL(fileURLWithPath: self.hubRoot)
            process.arguments = ["--json"]

            let output = Pipe()
            let error = Pipe()
            process.standardOutput = output
            process.standardError = error

            do {
                try process.run()
                process.waitUntilExit()
                let data = output.fileHandleForReading.readDataToEndOfFile()
                let status = try JSONDecoder().decode(HubStatus.self, from: data)
                completion(status)
            } catch {
                completion(nil)
            }
        }
    }

    private func apply(status: HubStatus?) {
        guard let status else {
            configureButton(title: "xAI X")
            stateItem.title = "AI Docs Hub: не удалось проверить"
            updatedItem.title = "Откройте статус или проверьте make hub-status"
            return
        }

        switch status.status {
        case "up":
            configureButton(title: "xAI")
            stateItem.title = "AI Docs Hub: работает"
        case "degraded":
            configureButton(title: "xAI !")
            stateItem.title = "AI Docs Hub: требует внимания"
        default:
            configureButton(title: "xAI X")
            stateItem.title = "AI Docs Hub: лежит"
        }

        let checked = status.checked_at ?? "только что"
        let runtime = status.components?["runtime"]?.message ?? "runtime не найден"
        updatedItem.title = "Проверено: \(checked) | \(runtime)"
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
