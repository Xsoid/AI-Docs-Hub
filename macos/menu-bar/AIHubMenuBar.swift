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

enum HubStatusRead {
    case success(HubStatus)
    case failure(String)
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let menu = NSMenu()
    private let stateItem = NSMenuItem(title: "AI Docs Hub: проверка...", action: nil, keyEquivalent: "")
    private let updatedItem = NSMenuItem(title: "Обновляется каждые 5 секунд", action: nil, keyEquivalent: "")
    private var timer: Timer?
    private var isRefreshing = false
    private let statusURL = URL(string: "http://localhost:4321/status/")!
    private let statusAPIURL = URL(string: "http://localhost:4321/api/hub-status.json")!
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
        readStatus { [weak self] result in
            DispatchQueue.main.async {
                self?.isRefreshing = false
                self?.apply(result: result)
            }
        }
    }

    private func readStatus(completion: @escaping (HubStatusRead) -> Void) {
        DispatchQueue.global(qos: .utility).async {
            let localResult = self.readStatusFromScript()
            if case .success = localResult {
                completion(localResult)
                return
            }
            self.readStatusFromAPI { apiResult in
                switch apiResult {
                case .success:
                    completion(apiResult)
                case .failure(let apiError):
                    if case .failure(let localError) = localResult {
                        completion(.failure("\(localError); API: \(apiError)"))
                    } else {
                        completion(apiResult)
                    }
                }
            }
        }
    }

    private func readStatusFromScript() -> HubStatusRead {
        guard let python = findPython() else {
            return .failure("python3.11 не найден")
        }

        let script = hubRoot + "/scripts/hub-status"
        let process = Process()
        process.executableURL = URL(fileURLWithPath: python)
        process.currentDirectoryURL = URL(fileURLWithPath: hubRoot)
        process.arguments = [script, "--json"]
        process.environment = processEnvironment()

        let output = Pipe()
        let error = Pipe()
        process.standardOutput = output
        process.standardError = error

        do {
            try process.run()
            process.waitUntilExit()
            let data = output.fileHandleForReading.readDataToEndOfFile()
            let errorData = error.fileHandleForReading.readDataToEndOfFile()
            if let status = decodeStatus(data) {
                return .success(status)
            }
            let detail = pipeText(errorData).isEmpty ? pipeText(data) : pipeText(errorData)
            return .failure("hub-status не вернул JSON (\(process.terminationStatus)): \(shortMessage(detail))")
        } catch {
            return .failure("hub-status не запустился: \(error.localizedDescription)")
        }
    }

    private func readStatusFromAPI(completion: @escaping (HubStatusRead) -> Void) {
        var request = URLRequest(
            url: statusAPIURL,
            cachePolicy: .reloadIgnoringLocalAndRemoteCacheData,
            timeoutInterval: 4
        )
        request.setValue("no-cache", forHTTPHeaderField: "cache-control")

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error {
                completion(.failure(error.localizedDescription))
                return
            }
            if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                completion(.failure("HTTP \(http.statusCode)"))
                return
            }
            guard let data, let status = self.decodeStatus(data) else {
                completion(.failure("API не вернул JSON"))
                return
            }
            completion(.success(status))
        }.resume()
    }

    private func findPython() -> String? {
        let fileManager = FileManager.default
        if let override = ProcessInfo.processInfo.environment["AI_DOCS_HUB_PYTHON"],
           !override.isEmpty,
           fileManager.isExecutableFile(atPath: override) {
            return override
        }

        for directory in mergedSearchPath().split(separator: ":") {
            let candidate = URL(fileURLWithPath: String(directory))
                .appendingPathComponent("python3.11")
                .path
            if fileManager.isExecutableFile(atPath: candidate) {
                return candidate
            }
        }

        for candidate in [
            "/opt/homebrew/opt/python@3.11/bin/python3.11",
            "/opt/homebrew/bin/python3.11",
            "/usr/local/opt/python@3.11/bin/python3.11",
            "/usr/local/bin/python3.11",
            "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"
        ] where fileManager.isExecutableFile(atPath: candidate) {
            return candidate
        }

        return nil
    }

    private func processEnvironment() -> [String: String] {
        var environment = ProcessInfo.processInfo.environment
        environment["PATH"] = mergedSearchPath()
        environment["PYTHONUNBUFFERED"] = "1"
        environment["ASTRO_TELEMETRY_DISABLED"] = "1"
        environment["npm_config_cache"] = hubRoot + "/.npm-cache"
        return environment
    }

    private func mergedSearchPath() -> String {
        var parts = (ProcessInfo.processInfo.environment["PATH"] ?? "")
            .split(separator: ":")
            .map(String.init)
        for candidate in [
            "/opt/homebrew/opt/python@3.11/bin",
            "/opt/homebrew/bin",
            "/usr/local/opt/python@3.11/bin",
            "/usr/local/bin",
            "/Library/Frameworks/Python.framework/Versions/3.11/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin"
        ] where !parts.contains(candidate) {
            parts.append(candidate)
        }
        return parts.joined(separator: ":")
    }

    private func decodeStatus(_ data: Data) -> HubStatus? {
        try? JSONDecoder().decode(HubStatus.self, from: data)
    }

    private func pipeText(_ data: Data) -> String {
        String(data: data, encoding: .utf8) ?? ""
    }

    private func shortMessage(_ value: String) -> String {
        let clean = value
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        if clean.isEmpty {
            return "пустой вывод"
        }
        if clean.count <= 160 {
            return clean
        }
        return String(clean.prefix(157)) + "..."
    }

    private func apply(result: HubStatusRead) {
        switch result {
        case .success(let status):
            apply(status: status)
        case .failure(let error):
            configureButton(title: "xAI X")
            stateItem.title = "AI Docs Hub: не удалось проверить"
            updatedItem.title = shortMessage(error)
        }
    }

    private func apply(status: HubStatus) {
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
