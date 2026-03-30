import Foundation

// El .app está en dist/WhisperClip.app
// El install dir es dos niveles arriba: dist/ -> whisperclip/
let bundleURL = Bundle.main.bundleURL
let installDir = bundleURL
    .deletingLastPathComponent()  // dist/
    .deletingLastPathComponent()  // whisperclip/

let venvPython = installDir
    .appendingPathComponent("venv/bin/python").path
let script = installDir
    .appendingPathComponent("whisperclip.py").path

let task = Process()
task.executableURL = URL(fileURLWithPath: venvPython)
task.arguments = [script]
task.currentDirectoryURL = installDir

do {
    try task.run()
    task.waitUntilExit()
} catch {
    fputs("WhisperClip: error al lanzar Python: \(error)\n", stderr)
    exit(1)
}
