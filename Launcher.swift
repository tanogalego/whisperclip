import Foundation

// El .app está en dist/WhisperClip.app
// El install dir es dos niveles arriba: dist/ -> whisperclip/
let bundleURL = Bundle.main.bundleURL
let installDir = bundleURL
    .deletingLastPathComponent()  // dist/
    .deletingLastPathComponent()  // whisperclip/

let venvPython = installDir.appendingPathComponent("venv/bin/python").path
let script     = installDir.appendingPathComponent("whisperclip.py").path

FileManager.default.changeCurrentDirectoryPath(installDir.path)

let task = Process()
task.executableURL = URL(fileURLWithPath: venvPython)
task.arguments = [script]
task.currentDirectoryURL = installDir

// Mantener este proceso vivo como padre de Python.
// macOS TCC atribuye los permisos (Accesibilidad, Input Monitoring, Micrófono)
// al bundle responsable = WhisperClip.app, que es este proceso padre.
// Los procesos hijo heredan ese contexto TCC.

// Propagar señales de terminación al proceso hijo
let signalHandler: @convention(c) (Int32) -> Void = { _ in
    task.terminate()
    exit(0)
}
signal(SIGTERM, signalHandler)
signal(SIGINT, signalHandler)

do {
    try task.run()
} catch {
    fputs("WhisperClip: error al lanzar Python: \(error)\n", stderr)
    exit(1)
}

// Esperar a que Python termine
task.waitUntilExit()
exit(task.terminationStatus)
