import AppKit
import ApplicationServices
import Darwin

setbuf(stdout, nil) // Preserva marcadores mesmo se o processo for interrompido.

// Macro nativo: a acessibilidade localiza os controles; CGEvent move/clica o mouse.
// Não acessa API, cookies, tokens, JavaScript ou CDP do Flow.
struct MacroError: Error, CustomStringConvertible {
    let description: String
    init(_ message: String) { description = message }
}

struct Options {
    var prompt: String?
    var prepare = false
    var inspect = false
    var configure = false
    var replace = false
    var reloadBefore = false
    var project: String?
    var keystrokes = true
    var reference: String?
    var receipt: String?

    init(_ args: [String]) throws {
        var i = 0
        while i < args.count {
            let arg = args[i]
            switch arg {
            case "--prompt", "--arquivo", "--projeto", "--elemento", "--recibo":
                i += 1
                guard i < args.count else { throw MacroError("Falta o valor de \(arg).") }
                if arg == "--recibo" { receipt = args[i] }
                else if arg == "--projeto" { project = args[i] }
                else if arg == "--elemento" {
                    guard !args[i].isEmpty, !args[i].contains("/"), !args[i].contains("\\"),
                          !args[i].unicodeScalars.contains(where: { $0.value < 32 }) else {
                        throw MacroError("--elemento deve ser o nome exato do arquivo já enviado ao projeto.")
                    }
                    reference = args[i]
                }
                else {
                    guard prompt == nil else { throw MacroError("Use só --prompt ou --arquivo.") }
                    prompt = arg == "--arquivo" ? try String(contentsOfFile: args[i], encoding: .utf8) : args[i]
                }
            case "--preparar": prepare = true
            case "--configurar": configure = true
            case "--inspecionar": inspect = true
            case "--substituir": replace = true
            case "--atualizar": reloadBefore = true
            case "--keystrokes": keystrokes = true
            case "--copiar": keystrokes = false
            case "--ajuda", "-h", "--help":
                print("""
                Uso: ./flow-macro --prompt 'SEU PROMPT'
                     ./flow-macro --arquivo prompt.txt
                     ./flow-macro --arquivo prompt.txt --preparar
                     ./flow-macro --configurar
                     ./flow-macro --inspecionar

                Padrões: Vídeo / Elementos / Veo 3.1 - Lite [Lower Priority] / 9:16 / 8s / x1.
                --preparar: configura e preenche, sem enviar.
                --configurar: só aplica e confere as configurações, sem preencher ou enviar.
                --inspecionar: só lê os controles visíveis.
                --projeto ID: exige esse projeto na aba ativa do Chrome.
                --substituir: permite substituir um prompt já preenchido.
                --atualizar: recarrega o projeto antes de selecionar referências recém-enviadas.
                --elemento NOME: seleciona o arquivo no seletor de Elementos com mouse e teclado.
                --recibo ARQUIVO: diário persistente antes do clique, para retomada sem envio duplicado.
                --keystrokes: digita por press/release (padrão).
                --copiar: usa clipboard/Cmd+V apenas quando solicitado.
                Pare com Esc, Ctrl+C no terminal ou mouse no canto superior esquerdo.
                """)
                exit(0)
            default: throw MacroError("Opção desconhecida: \(arg). Use --ajuda.")
            }
            i += 1
        }
        if let text = prompt {
            prompt = text.replacingOccurrences(of: "\r\n", with: "\n").replacingOccurrences(of: "\r", with: "\n")
            if keystrokes && prompt!.unicodeScalars.contains(where: { ($0.value < 32 && $0.value != 10) || $0.value == 127 }) {
                throw MacroError("O modo --keystrokes aceita texto e quebras de linha, sem tabulações ou controles.")
            }
        }
        if inspect || configure {
            guard prompt == nil && !prepare && !(inspect && configure) else {
                throw MacroError("--inspecionar e --configurar são modos independentes.")
            }
        } else {
            guard let text = prompt, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw MacroError("Informe --prompt ou --arquivo. Use --ajuda.")
            }
        }
    }
}

func attr(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success else { return nil }
    return value
}
func stringAttr(_ e: AXUIElement, _ name: String) -> String { attr(e, name) as? String ?? "" }
func labels(_ e: AXUIElement) -> [String] {
    ["AXTitle", "AXDescription", "AXValue", "AXHelp"].map { stringAttr(e, $0) }.filter { !$0.isEmpty }
}
func role(_ e: AXUIElement) -> String { stringAttr(e, "AXRole") }
func children(_ e: AXUIElement) -> [AXUIElement] { attr(e, "AXChildren") as? [AXUIElement] ?? [] }
func tree(_ root: AXUIElement) -> [AXUIElement] {
    var result: [AXUIElement] = []
    func visit(_ e: AXUIElement, _ depth: Int) {
        // AXChildren não inclui o pai. CFHash não é uma identidade única de elementos AX.
        guard depth < 50, result.count < 12000 else { return }
        result.append(e)
        for child in children(e) { visit(child, depth + 1) }
    }
    visit(root, 0)
    return result
}
func rect(_ e: AXUIElement) -> CGRect? {
    guard let p = attr(e, "AXPosition"), CFGetTypeID(p) == AXValueGetTypeID(),
          let s = attr(e, "AXSize"), CFGetTypeID(s) == AXValueGetTypeID() else { return nil }
    var point = CGPoint.zero
    var size = CGSize.zero
    guard AXValueGetValue(p as! AXValue, .cgPoint, &point),
          AXValueGetValue(s as! AXValue, .cgSize, &size), size.width > 0, size.height > 0 else { return nil }
    return CGRect(origin: point, size: size)
}
func selected(_ e: AXUIElement) -> Bool {
    (attr(e, "AXValue") as? NSNumber)?.intValue == 1 || stringAttr(e, "AXValue") == "1"
        || (attr(e, "AXSelected") as? Bool) == true
}

final class FlowMacro {
    let app: NSRunningApplication
    let ax: AXUIElement
    let options: Options
    var originalURL = ""
    let model = "Veo 3.1 - Lite [Lower Priority]"
    let radios = ["Vídeo", "Elementos", "9:16", "8s", "x1"]

    init(_ options: Options) throws {
        self.options = options
        guard AXIsProcessTrusted() else {
            throw MacroError("O macOS não liberou a Acessibilidade para este processo. Em Ajustes do Sistema > Privacidade e Segurança > Acessibilidade, autorize o app que executa o macro (Terminal ou Codex); se necessário adicione também o executável .local-bin/flow-macro. Depois execute novamente.")
        }
        guard let chrome = NSRunningApplication.runningApplications(withBundleIdentifier: "com.google.Chrome").first else {
            throw MacroError("Abra o Chrome no projeto do Flow antes de executar.")
        }
        app = chrome
        ax = AXUIElementCreateApplication(chrome.processIdentifier)
        AXUIElementSetMessagingTimeout(ax, 2)
        AXUIElementSetAttributeValue(ax, "AXManualAccessibility" as CFString, kCFBooleanTrue)
        AXUIElementSetAttributeValue(ax, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
        // Só lê a janela principal; nunca troca a aba ou escolhe outra conta.
        originalURL = try currentURL()
        try validateURL(originalURL)
    }

    func window() throws -> AXUIElement {
        guard let value = attr(ax, "AXMainWindow"), CFGetTypeID(value) == AXUIElementGetTypeID() else {
            throw MacroError("Não foi possível ler a janela principal do Chrome.")
        }
        return value as! AXUIElement
    }
    func nodes() throws -> [AXUIElement] { tree(try window()) }
    func currentURL() throws -> String {
        let web = try nodes().filter { role($0) == "AXWebArea" }
        guard let area = web.first else {
            let counts = Dictionary(grouping: try nodes(), by: { role($0) }).map { "\($0.key)=\($0.value.count)" }.sorted().joined(separator: ", ")
            throw MacroError("Não achei o conteúdo da aba. Abra o projeto do Flow no Chrome. Controles: \(counts)")
        }
        if let url = attr(area, "AXURL") as? URL { return url.absoluteString }
        if let url = attr(area, "AXURL") as? String { return url }
        throw MacroError("Não consegui confirmar a URL da aba ativa.")
    }
    func validateURL(_ text: String) throws {
        guard let url = URL(string: text), url.scheme == "https", url.host == "flow.google.com",
              url.path.components(separatedBy: "/").contains("project") else {
            throw MacroError("A aba ativa precisa ser um projeto em https://flow.google.com/.")
        }
        if let project = options.project {
            let parts = url.path.components(separatedBy: "/")
            guard let index = parts.firstIndex(of: "project"), index + 1 < parts.count,
                  parts[index + 1] == project else { throw MacroError("A aba ativa não corresponde ao --projeto informado.") }
        }
    }
    func checkStop(_ foreground: Bool = true) throws {
        if let session = CGSessionCopyCurrentDictionary() as? [String: Any],
           session["CGSSessionScreenIsLocked"] as? Bool == true {
            throw MacroError("Sessão do macOS bloqueada. Nenhum novo envio autorizado até desbloquear.")
        }
        if CGEventSource.keyState(.combinedSessionState, key: 53) { throw MacroError("Interrompido por Esc.") }
        if let p = CGEvent(source: nil)?.location, p.x >= 0 && p.x < 5 && p.y >= 0 && p.y < 5 {
            throw MacroError("Interrompido: mouse no canto superior esquerdo.")
        }
        if foreground && (attr(ax, "AXFrontmost") as? Bool) != true {
            throw MacroError("O Chrome perdeu o foco. Macro interrompido.")
        }
    }
    func pause(_ seconds: Double) throws {
        let end = Date().addingTimeInterval(seconds)
        repeat { try checkStop(); Thread.sleep(forTimeInterval: 0.025) } while Date() < end
    }
    func find(_ name: String, roles: [String]? = nil) throws -> AXUIElement? {
        let matches = try nodes().filter { e in
            (roles == nil || roles!.contains(role(e))) && labels(e).contains(name) && rect(e) != nil
        }
        guard matches.count <= 1 else { throw MacroError("Controle ambíguo: \(name). Nada será clicado.") }
        return matches.first
    }
    func require(_ name: String, roles: [String]? = nil, timeout: Double = 5) throws -> AXUIElement {
        let end = Date().addingTimeInterval(timeout)
        repeat {
            try checkStop()
            if let e = try find(name, roles: roles) { return e }
            try pause(0.15)
        } while Date() < end
        throw MacroError("Controle não encontrado: \(name). A interface pode ter mudado.")
    }
    func click(_ e: AXUIElement, dismissSettingsBackdrop: Bool = false) throws {
        try checkStop()
        guard try currentURL() == originalURL else { throw MacroError("A aba mudou; clique cancelado.") }
        guard (attr(e, "AXEnabled") as? Bool) != false, let box = rect(e) else {
            throw MacroError("Controle indisponível; clique cancelado.")
        }
        let target = CGPoint(x: box.midX, y: box.midY)
        guard let bounds = rect(try window()), bounds.contains(target) else { throw MacroError("Controle fora da janela.") }
        let origin = CGEvent(source: nil)?.location ?? target
        for step in 1...10 {
            try checkStop()
            let t = Double(step) / 10
            let smooth = t * t * (3 - 2 * t)
            let p = CGPoint(x: origin.x + (target.x - origin.x) * smooth, y: origin.y + (target.y - origin.y) * smooth)
            CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)
            Thread.sleep(forTimeInterval: 0.01)
        }
        try checkStop()
        var hit: AXUIElement?
        guard AXUIElementCopyElementAtPosition(ax, Float(target.x), Float(target.y), &hit) == .success,
              var actual = hit else { throw MacroError("Não foi possível conferir o controle sob o mouse.") }
        func hasAncestor(_ start: AXUIElement, _ expected: AXUIElement) -> Bool {
            var current = start
            for _ in 0..<8 {
                if CFEqual(current, expected) { return true }
                if role(current) == role(expected), let a = rect(current), let b = rect(expected),
                   abs(a.midX - b.midX) < 1, abs(a.midY - b.midY) < 1,
                   abs(a.width - b.width) < 1, abs(a.height - b.height) < 1,
                   !Set(labels(current)).intersection(Set(labels(expected))).isEmpty { return true }
                guard let p = attr(current, "AXParent"), CFGetTypeID(p) == AXUIElementGetTypeID() else { return false }
                current = p as! AXUIElement
            }
            return false
        }
        // O painel usa um backdrop transparente sobre o gatilho; clicar nele fecha o painel.
        var isSettingsBackdrop = false
        if dismissSettingsBackdrop && role(actual) == "AXGroup" && labels(e).contains("Gatilho de configurações") {
            isSettingsBackdrop = try find("9:16", roles: ["AXRadioButton"]) != nil
        }
        // Um backdrop pode sobreviver alguns frames após o painel sumir do AX.
        // Só espera e refaz o hit-test; nenhum clique é repetido aqui.
        let hitDeadline = Date().addingTimeInterval(2.5)
        while !hasAncestor(actual, e) && !isSettingsBackdrop && Date() < hitDeadline {
            try pause(0.15)
            guard try currentURL() == originalURL, let freshBox = rect(e),
                  abs(freshBox.midX - box.midX) < 1, abs(freshBox.midY - box.midY) < 1 else {
                throw MacroError("O controle mudou de posição durante a espera. Clique cancelado.")
            }
            var freshHit: AXUIElement?
            if AXUIElementCopyElementAtPosition(ax, Float(target.x), Float(target.y), &freshHit) == .success,
               let value = freshHit { actual = value }
        }
        guard hasAncestor(actual, e) || isSettingsBackdrop else {
            throw MacroError("O controle sob o mouse mudou. Esperado: \(role(e)) \(labels(e).first ?? ""); encontrado: \(role(actual)) \(labels(actual).first ?? "") em \(String(describing: rect(actual))); alvo \(box); mouse \(String(describing: CGEvent(source: nil)?.location)). Clique cancelado.")
        }
        CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: target, mouseButton: .left)?.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: 0.06)
        CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: target, mouseButton: .left)?.post(tap: .cghidEventTap)
        try pause(0.25)
    }
    func key(_ code: CGKeyCode, flags: CGEventFlags = []) throws {
        try checkStop()
        for down in [true, false] {
            let event = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down)
            event?.flags = flags
            event?.post(tap: .cghidEventTap)
        }
        try pause(0.12)
    }
    func stroke(_ code: CGKeyCode = 0, text: String? = nil, flags: CGEventFlags = [], delay: Double = 0.001) throws {
        try checkStop()
        guard let down = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: true),
              let up = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: false) else {
            throw MacroError("Não foi possível criar os eventos press/release. Digitação interrompida.")
        }
        down.flags = flags
        up.flags = flags
        down.setIntegerValueField(.keyboardEventAutorepeat, value: 0)
        up.setIntegerValueField(.keyboardEventAutorepeat, value: 0)
        if let text = text {
            let units = Array(text.utf16)
            units.withUnsafeBufferPointer { buffer in
                down.keyboardSetUnicodeString(stringLength: units.count, unicodeString: buffer.baseAddress)
                up.keyboardSetUnicodeString(stringLength: units.count, unicodeString: buffer.baseAddress)
            }
        }
        down.post(tap: .cghidEventTap)
        // Sempre libera a tecla antes de testar interrupções novamente.
        Thread.sleep(forTimeInterval: delay)
        up.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: delay)
    }
    func verifyEditorFocus(_ field: AXUIElement) throws {
        try checkStop()
        guard let value = attr(ax, "AXFocusedUIElement"), CFGetTypeID(value) == AXUIElementGetTypeID() else {
            throw MacroError("O campo de prompt perdeu o foco. Digitação interrompida.")
        }
        let focused = value as! AXUIElement
        if CFEqual(focused, field) { return }
        // React pode recriar o nó durante atualização do inventário. Continua só
        // se o foco real estiver no único editor atual da mesma aba/projeto.
        let current = try editor()
        guard CFEqual(focused, current), labels(current).contains("O que você quer criar?"),
              try currentURL() == originalURL else {
            throw MacroError("O campo de prompt perdeu o foco. Digitação interrompida. Controle atual: \(role(focused)) \(stringAttr(focused, "AXDescription"))")
        }
    }
    func ensureSettings() throws {
        if try find("9:16", roles: ["AXRadioButton"]) == nil {
            try click(require("Gatilho de configurações", roles: ["AXButton"]))
        }
        _ = try require("9:16", roles: ["AXRadioButton"])
    }
    func chooseRadio(_ name: String) throws {
        let e = try require(name, roles: ["AXRadioButton"])
        // As opções já corretas são conferidas sem cliques redundantes.
        if !selected(e) { try click(e) }
        guard selected(try require(name, roles: ["AXRadioButton"])) else {
            throw MacroError("O Flow não confirmou a opção \(name).")
        }
    }
    func configure() throws {
        try ensureSettings()
        for name in radios.prefix(3) { try chooseRadio(name) }
        try click(require("Selecionar família de modelos", roles: ["AXPopUpButton", "AXButton"]))
        // O menu do Flow expõe itens sem role de botão; a caixa acessível basta para o clique real.
        try click(require(model))
        for name in radios.suffix(2) { try chooseRadio(name) }
        for name in radios {
            guard selected(try require(name, roles: ["AXRadioButton"])) else { throw MacroError("Configuração divergiu: \(name).") }
        }
        guard try nodes().contains(where: { labels($0).contains("0 créditos") }) else {
            throw MacroError("O Flow não confirmou 0 créditos. Envio cancelado.")
        }
        try click(require("Gatilho de configurações", roles: ["AXButton"]), dismissSettingsBackdrop: true)
        guard try find("9:16", roles: ["AXRadioButton"]) == nil else { throw MacroError("O painel de configurações não fechou.") }
        print("Configurações conferidas: Vídeo / Elementos / \(model) / 9:16 / 8s / x1 / 0 créditos.")
    }
    func editor() throws -> AXUIElement { try require("O que você quer criar?", roles: ["AXTextArea", "AXTextField"]) }
    func verifyPreparedConfiguration() throws {
        try ensureSettings()
        defer { try? click(require("Gatilho de configurações", roles: ["AXButton"]), dismissSettingsBackdrop: true) }
        for name in radios {
            guard selected(try require(name, roles: ["AXRadioButton"])) else {
                throw MacroError("Configuração mudou depois da preparação: \(name). Nenhuma geração enviada.")
            }
        }
        guard try nodes().contains(where: { labels($0).contains("0 créditos") }) else {
            throw MacroError("O Flow não confirmou 0 créditos depois da preparação. Nenhuma geração enviada.")
        }
        print("Configuração final e 0 créditos reconferidos após referência e prompt.")
    }
    func promptValue() throws -> String { stringAttr(try editor(), "AXValue") }
    func clean(_ text: String) -> String { text.trimmingCharacters(in: .newlines) }
    func refreshProject() throws {
        try key(53) // Fecha o seletor, caso esteja aberto.
        guard try currentURL() == originalURL else { throw MacroError("A aba mudou antes da atualização.") }
        try key(15, flags: .maskCommand) // Cmd+R nativo: atualiza a biblioteca desta aba.
        try pause(0.8)
        let deadline = Date().addingTimeInterval(30)
        repeat {
            try checkStop()
            if let url = try? currentURL(), url == originalURL,
               (try? find("Gatilho de configurações", roles: ["AXButton"])) != nil,
               (try? find("O que você quer criar?", roles: ["AXTextArea", "AXTextField"])) != nil {
                try pause(0.6)
                print("Projeto atualizado; biblioteca da aba principal sincronizada.")
                return
            }
            try pause(0.2)
        } while Date() < deadline
        throw MacroError("O projeto não terminou de carregar após atualizar. Nenhuma geração enviada.")
    }
    func referenceChoice(_ name: String, timeout: Double) throws -> AXUIElement? {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            try checkStop()
            if let option = try find(name + " Imagem") { return option }
            if let label = try find(name, roles: ["AXStaticText"]) { return label }
            if let preview = try find("Prévia de " + name, roles: ["AXImage"]) { return preview }
            try pause(0.2)
        } while Date() < deadline
        return nil
    }
    func selectReference(_ name: String, mayRefresh: Bool = true) throws {
        // Configuração e seleção acontecem inteiramente pelo mouse/teclado nativos.
        if let clear = try find("Apagar comando", roles: ["AXButton"]) { try click(clear) }
        try click(require("Adicionar elementos à caixa de comando", roles: ["AXButton", "AXPopUpButton"]))
        let search = try require("Pesquisar recursos", roles: ["AXTextField", "AXTextArea", "AXSearchField", "AXComboBox"])
        try click(search)
        try verifyEditorFocus(search)
        try key(0, flags: .maskCommand)
        for scalar in name.unicodeScalars {
            try verifyEditorFocus(search)
            try stroke(text: String(scalar))
        }
        try pause(0.35)
        // O seletor expõe a opção com sufixo Imagem; algumas versões expõem só o texto.
        guard let choice = try referenceChoice(name, timeout: 12) else {
            if mayRefresh {
                print("Referência ainda ausente na aba principal; atualizando antes de repetir somente a busca: \(name).")
                try refreshProject()
                try configure()
                try pause(0.8)
                try selectReference(name, mayRefresh: false)
                return
            }
            throw MacroError("Referência não disponível após atualizar e aguardar: \(name). Nenhuma geração enviada.")
        }
        // A busca exata pode selecionar automaticamente o único resultado.
        if try find("Prévia de " + name, roles: ["AXImage"]) == nil { try click(choice) }
        if try find("Pesquisar recursos", roles: ["AXTextField", "AXTextArea", "AXSearchField", "AXComboBox"]) != nil {
            _ = try require("Prévia de " + name, roles: ["AXImage"])
            try click(require("Incluir no comando", roles: ["AXButton"]))
        }
        let deadline = Date().addingTimeInterval(6)
        while try find("Pesquisar recursos", roles: ["AXTextField", "AXTextArea", "AXSearchField", "AXComboBox"]) != nil {
            guard Date() < deadline else { throw MacroError("O seletor do elemento não fechou. Nenhuma geração enviada.") }
            try pause(0.15)
        }
        _ = try require("Elemento", roles: ["AXButton"])
        print("Elemento selecionado pelo macro: \(name).")
    }
    func fillByKeystrokes(_ prompt: String) throws {
        let field = try editor()
        let old = stringAttr(field, "AXValue")
        guard old.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || clean(old) == clean(prompt) || options.replace else {
            throw MacroError("Já existe um prompt no campo. Use --substituir para autorizar a troca.")
        }
        try click(field)
        guard let focused = attr(ax, "AXFocusedUIElement"), CFEqual(focused, field) else {
            throw MacroError("O campo de prompt não recebeu o foco. Digitação cancelada.")
        }
        let typingStarted = Date()
        for attempt in 0..<2 {
            try verifyEditorFocus(field)
            guard try currentURL() == originalURL else { throw MacroError("A aba mudou durante a digitação.") }
            try key(0, flags: .maskCommand) // Substitui somente o texto desta preparação.
            let delay = attempt == 0 ? 0.002 : 0.003
            var strokes = 0
            for scalar in prompt.unicodeScalars {
                if strokes % 16 == 0 || scalar.value == 10 { try verifyEditorFocus(field) }
                if strokes % 128 == 0 {
                    guard try currentURL() == originalURL else { throw MacroError("A aba mudou durante a digitação.") }
                }
                if scalar.value == 10 {
                    try stroke(36, flags: .maskShift, delay: delay)
                } else {
                    try stroke(text: String(scalar), delay: delay)
                }
                strokes += 1
                // Deixa o editor consumir os eventos sem acumular uma fila longa.
                if strokes % 64 == 0 { try pause(0.025) }
            }
            let deadline = Date().addingTimeInterval(5)
            var exact = false
            repeat {
                try verifyEditorFocus(field)
                if clean(try promptValue()) == clean(prompt) { exact = true; break }
                try pause(0.1)
            } while Date() < deadline
            if exact {
                print("Prompt digitado por press/release e conferido (\(prompt.count) caracteres, \(strokes) pares de eventos, \(String(format: "%.2f", Date().timeIntervalSince(typingStarted)))s, tentativa \(attempt + 1)).")
                return
            }
            if attempt == 0 {
                print("O editor alterou o texto. Corrigindo somente a digitação com intervalo conservador, antes de qualquer envio.")
            }
        }
        throw MacroError("O texto digitado não confere após corrigir a digitação. Envio cancelado; nenhum clique em gerar.")
    }
    func fill(_ prompt: String) throws {
        if options.keystrokes { try fillByKeystrokes(prompt) }
        else { try fillByPaste(prompt) }
    }
    func fillByPaste(_ prompt: String) throws {
        let field = try editor()
        let old = stringAttr(field, "AXValue")
        guard old.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || clean(old) == clean(prompt) || options.replace else {
            throw MacroError("Já existe um prompt no campo. Use --substituir para autorizar a troca.")
        }
        try click(field)
        guard let focused = attr(ax, "AXFocusedUIElement"), CFEqual(focused, field) else {
            throw MacroError("O campo de prompt não recebeu o foco. Digitação cancelada.")
        }
        let pasteboard = NSPasteboard.general
        let saved = (pasteboard.pasteboardItems ?? []).map { item in
            item.types.compactMap { type -> (NSPasteboard.PasteboardType, Data)? in
                guard let data = item.data(forType: type) else { return nil }
                return (type, data)
            }
        }
        pasteboard.clearContents()
        pasteboard.setString(prompt, forType: .string)
        let ourChange = pasteboard.changeCount
        defer {
            // Preserva uma cópia nova feita pelo usuário durante a execução.
            if pasteboard.changeCount == ourChange {
                pasteboard.clearContents()
                let items = saved.map { values -> NSPasteboardItem in
                    let item = NSPasteboardItem()
                    for (type, data) in values { item.setData(data, forType: type) }
                    return item
                }
                if !items.isEmpty { pasteboard.writeObjects(items) }
            }
        }
        try key(0, flags: .maskCommand) // Cmd+A, só dentro do editor verificado.
        try key(9, flags: .maskCommand) // Cmd+V, Unicode e múltiplas linhas.
        try pause(0.3)
        guard clean(try promptValue()) == clean(prompt) else { throw MacroError("O texto preenchido não confere. Envio cancelado.") }
        print("Prompt colado e conferido (\(prompt.count) caracteres).")
    }
    func run() throws {
        if options.inspect {
            for e in try nodes() {
                let r = role(e)
                let names = labels(e)
                if ["AXRadioButton", "AXPopUpButton", "AXMenuItem"].contains(r)
                    || names.contains("Gatilho de configurações") || names.contains("Iniciar geração")
                    || names.contains("O que você quer criar?") || names.contains(model) {
                    // Não inclui valores de campos de texto nem dados da conta.
                    let name = r == "AXTextArea" ? "O que você quer criar?" : names.filter { $0.count < 100 }.joined(separator: " | ")
                    print("\(r): \(name) [selecionado=\(selected(e))]")
                }
            }
            return
        }
        print("O macro vai trazer o Chrome à frente. Esc ou canto superior esquerdo interrompem.")
        app.activate(options: [])
        AXUIElementPerformAction(try window(), kAXRaiseAction as CFString)
        AXUIElementSetAttributeValue(ax, kAXFrontmostAttribute as CFString, kCFBooleanTrue)
        let focusDeadline = Date().addingTimeInterval(3)
        while (attr(ax, "AXFrontmost") as? Bool) != true {
            try checkStop(false)
            guard Date() < focusDeadline else { throw MacroError("O Chrome não recebeu o foco.") }
            Thread.sleep(forTimeInterval: 0.05)
        }
        try pause(0.3)
        guard try currentURL() == originalURL else { throw MacroError("A aba mudou; macro cancelado.") }
        // Não mexe no painel se já houver texto que o usuário não autorizou substituir.
        if let prompt = options.prompt {
            let old = try promptValue()
            guard old.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || clean(old) == clean(prompt) || options.replace else {
                throw MacroError("Já existe um prompt. Use --substituir para autorizar a troca.")
            }
        }
        if options.reloadBefore { try refreshProject() }
        try configure()
        // Aguarda o backdrop do painel deixar de capturar o hit-test.
        try pause(0.8)
        if options.configure { print("Concluído sem preencher nem gerar."); return }
        if let reference = options.reference { try selectReference(reference) }
        let prompt = options.prompt!
        try fill(prompt)
        try verifyPreparedConfiguration()
        if options.prepare { print("Preparado, sem enviar. O botão Iniciar geração não foi clicado."); return }
        guard try currentURL() == originalURL else { throw MacroError("A aba mudou antes do envio.") }
        guard clean(try promptValue()) == clean(prompt) else { throw MacroError("O prompt mudou antes do envio.") }
        let generate = try require("Iniciar geração", roles: ["AXButton"])
        guard (attr(generate, "AXEnabled") as? Bool) == true else {
            throw MacroError("Iniciar geração está desabilitado. Confira os elementos de referência.")
        }
        try nativeReceipt(options, phase: "click_intent")
        print("Clicando uma única vez em Iniciar geração…")
        try click(generate)
        // Nunca repete o envio, mesmo se o Flow demorar ou apresentar erro.
        let deadline = Date().addingTimeInterval(15)
        repeat {
            try pause(0.4)
            if try currentURL() != originalURL { throw MacroError("A aba mudou após o clique. Confira o Flow; o envio não será repetido.") }
            if (try promptValue()).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                print("O Flow limpou o prompt após o clique. Submissão observada; acompanhe a geração na página.")
                try nativeReceipt(options, phase: "submitted_ui")
                return
            }
        } while Date() < deadline
        throw MacroError("O botão foi clicado uma vez, mas o Flow não limpou o prompt em 15s. Confira a página antes de tentar novamente; o macro não repetiu o envio.")
    }
}

func sharedLockPath() -> String {
    let environment = ProcessInfo.processInfo.environment
    if let explicit = environment["FLOW_LOCK"], !explicit.isEmpty { return explicit }
    if let directory = environment["FLOW_SYSTEM_DIR"] ?? Bundle.main.object(forInfoDictionaryKey: "FlowSystemDirectory") as? String {
        return URL(fileURLWithPath: directory).appendingPathComponent(".flow_lane.lock").path
    }
    return URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent(".flow_lane.lock").path
}

func nativeReceipt(_ options: Options, phase: String) throws {
    guard let path = options.receipt else { return }
    let value: [String: Any] = ["phase": phase, "pid": ProcessInfo.processInfo.processIdentifier,
                                "at": Date().timeIntervalSince1970]
    let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    try data.write(to: URL(fileURLWithPath: path), options: .atomic)
    let file = try FileHandle(forWritingTo: URL(fileURLWithPath: path))
    try file.synchronize()
    try file.close()
}

func execute(_ options: Options, lockPath: String) throws {
    var controllerFD: Int32 = -1
    if ProcessInfo.processInfo.environment["FLOW_CONTROLLER_CHILD"] != "1" {
        let path = URL(fileURLWithPath: lockPath).deletingLastPathComponent().appendingPathComponent(".flow_controller.lock").path
        controllerFD = open(path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
        guard controllerFD >= 0, flock(controllerFD, LOCK_EX | LOCK_NB) == 0 else {
            if controllerFD >= 0 { close(controllerFD) }
            throw MacroError("Um controlador está usando o Flow. Não iniciar outro macro durante a produção.")
        }
    }
    defer { if controllerFD >= 0 { flock(controllerFD, LOCK_UN); close(controllerFD) } }
    let fd = open(lockPath, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
    guard fd >= 0 else { throw MacroError("Não foi possível abrir o lock local.") }
    defer { close(fd) }
    guard flock(fd, LOCK_EX | LOCK_NB) == 0 else { throw MacroError("Outra automação está usando o Flow. Aguarde terminar.") }
    defer { flock(fd, LOCK_UN) }
    try nativeReceipt(options, phase: "preparing")
    try FlowMacro(options).run()
    if options.configure || options.prepare { try nativeReceipt(options, phase: "prepared_without_click") }
}

final class MacroApp: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    let input = NSTextView()
    let status = NSTextField(wrappingLabelWithString: "Abra o projeto do Flow na aba ativa do Chrome. Cole o prompt abaixo.")
    var buttons: [NSButton] = []

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 700, height: 430),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Macro Flow"
        let content = window.contentView!
        let title = NSTextField(labelWithString: "Vídeo · Elementos · Lite Lower Priority · 9:16 · 8s · x1")
        title.frame = NSRect(x: 24, y: 386, width: 650, height: 22)
        content.addSubview(title)
        let scroll = NSScrollView(frame: NSRect(x: 24, y: 150, width: 652, height: 220))
        scroll.borderType = .bezelBorder
        scroll.hasVerticalScroller = true
        input.isRichText = false
        input.frame = NSRect(x: 0, y: 0, width: 652, height: 220)
        input.font = NSFont.systemFont(ofSize: 15)
        input.isVerticallyResizable = true
        input.isHorizontallyResizable = false
        input.textContainer?.widthTracksTextView = true
        input.autoresizingMask = [.width]
        input.minSize = NSSize(width: 0, height: 220)
        input.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        input.setAccessibilityLabel("Prompt do macro")
        scroll.documentView = input
        content.addSubview(scroll)
        let actions: [(String, Selector, CGFloat, CGFloat)] = [
            ("Permissão", #selector(permission), 24, 110),
            ("Configurar padrões", #selector(configureOnly), 145, 165),
            ("Preparar sem gerar", #selector(prepareOnly), 321, 170),
            ("Enviar no Flow", #selector(submit), 502, 174)
        ]
        for (name, action, x, width) in actions {
            let button = NSButton(title: name, target: self, action: action)
            button.bezelStyle = .rounded
            button.frame = NSRect(x: x, y: 103, width: width, height: 32)
            content.addSubview(button)
            buttons.append(button)
        }
        status.frame = NSRect(x: 24, y: 22, width: 652, height: 68)
        status.setAccessibilityLabel("Estado do macro")
        content.addSubview(status)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        if !AXIsProcessTrusted() { status.stringValue = "Clique em Permissão para autorizar o Macro Flow nos ajustes do macOS." }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    @objc func permission() {
        let request = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        let allowed = AXIsProcessTrustedWithOptions(request)
        status.stringValue = allowed ? "Acessibilidade autorizada. Pronto para operar o Flow." : "Autorize Macro Flow em Privacidade e Segurança → Acessibilidade (ou Controle de dispositivos e acesso a dados)."
    }
    @objc func configureOnly() { start(["--configurar"]) }
    @objc func prepareOnly() { start(["--prompt", input.string, "--preparar"]) }
    @objc func submit() { start(["--prompt", input.string]) }
    func start(_ args: [String]) {
        guard AXIsProcessTrusted() else { permission(); return }
        let options: Options
        do { options = try Options(args) } catch { status.stringValue = "\(error)"; return }
        buttons.forEach { $0.isEnabled = false }
        status.stringValue = "Executando. Não mexa no mouse ou teclado. Esc ou canto superior esquerdo interrompem."
        let lock = sharedLockPath()
        DispatchQueue.global(qos: .userInitiated).async {
            let message: String
            do {
                try execute(options, lockPath: lock)
                message = options.configure ? "Padrões selecionados e conferidos. Nenhuma geração disparada."
                    : options.prepare ? "Prompt e padrões conferidos. Preparado sem gerar."
                    : "O Flow limpou o prompt após o clique. Acompanhe a geração no Chrome."
            } catch { message = "\(error)" }
            DispatchQueue.main.async {
                self.status.stringValue = message
                self.buttons.forEach { $0.isEnabled = true }
                self.window.makeKeyAndOrderFront(nil)
                NSApp.activate(ignoringOtherApps: true)
            }
        }
    }
}

if CommandLine.arguments.count == 1 && Bundle.main.bundleURL.pathExtension == "app" {
    let application = NSApplication.shared
    application.setActivationPolicy(.regular)
    let delegate = MacroApp()
    application.delegate = delegate
    withExtendedLifetime(delegate) { application.run() }
    exit(0)
}

if Array(CommandLine.arguments.dropFirst()) == ["--pedir-permissao"] {
    let request = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
    let allowed = AXIsProcessTrustedWithOptions(request)
    print(allowed ? "Acessibilidade já autorizada." : "Pedido de Acessibilidade enviado ao macOS. Autorize o macro na janela do sistema.")
    exit(0)
}

do {
    let options = try Options(Array(CommandLine.arguments.dropFirst()))
    let lockPath = sharedLockPath()
    try execute(options, lockPath: lockPath)
} catch {
    fputs("ERRO: \(error)\n", stderr)
    exit(1)
}
