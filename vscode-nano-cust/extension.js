const path = require("path");
const os = require("os");
const fs = require("fs/promises");
const { spawn } = require("child_process");
const vscode = require("vscode");

const LANGUAGE_ID = "nano-cust";
const DIAGNOSTIC_SOURCE = "nano_cust";
const ANSI_ESCAPE = /\u001b\[[0-?]*[ -/]*[@-~]/g;

function stripAnsi(value) {
  return value.replace(ANSI_ESCAPE, "");
}

function compilerPath(document) {
  const configured = vscode.workspace.getConfiguration("nanoCust", document.uri)
    .get("compilerPath", "");
  if (configured) {
    return configured;
  }
  const folder = vscode.workspace.getWorkspaceFolder(document.uri);
  return folder ? path.join(folder.uri.fsPath, "main.py") : "";
}

function diagnosticFromOutput(document, output) {
  const plain = stripAnsi(output);
  const location = plain.match(/File "<source>", line (\d+)/);
  const error = plain.match(/(?:Kinako\w*Error|ValueError):\s*([^\r\n]+)/);
  const line = location ? Math.max(0, Number(location[1]) - 1) : 0;
  const text = document.lineAt(Math.min(line, document.lineCount - 1)).text;
  const message = error ? error[1] : "構文または型のチェックに失敗しました。";
  return new vscode.Diagnostic(
    new vscode.Range(line, 0, line, Math.max(1, text.length)),
    message,
    vscode.DiagnosticSeverity.Error,
  );
}

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection(DIAGNOSTIC_SOURCE);
  const pending = new Map();

  async function check(document) {
    if (document.languageId !== LANGUAGE_ID || document.isUntitled) {
      return;
    }

    const compiler = compilerPath(document);
    if (!compiler) {
      diagnostics.set(document.uri, [new vscode.Diagnostic(
        new vscode.Range(0, 0, 0, 1),
        "main.py が見つかりません。設定 nanoCust.compilerPath でコンパイラのパスを指定してください。",
        vscode.DiagnosticSeverity.Warning,
      )]);
      return;
    }

    const pythonPath = vscode.workspace.getConfiguration("nanoCust", document.uri)
      .get("pythonPath", "python");
    const version = document.version;
    let output = "";
    const temporaryDirectory = await fs.mkdtemp(path.join(os.tmpdir(), "nano-cust-"));
    const temporarySource = path.join(temporaryDirectory, "source.nc");
    await fs.writeFile(temporarySource, document.getText(), "utf8");

    const result = await new Promise((resolve) => {
      const child = spawn(pythonPath, [compiler, temporarySource, "--check"], {
        cwd: path.dirname(compiler),
        windowsHide: true,
        env: {
          ...process.env,
          PYTHONIOENCODING: "utf-8",
          PYTHONUTF8: "1",
        },
      });
      child.stdout.on("data", (data) => { output += data.toString("utf8"); });
      child.stderr.on("data", (data) => { output += data.toString("utf8"); });
      child.on("error", (error) => resolve({ code: 1, error }));
      child.on("close", (code) => resolve({ code, error: null }));
    }).finally(() => fs.rm(temporaryDirectory, { recursive: true, force: true }));

    if (document.version !== version) {
      return;
    }
    if (result.error) {
      diagnostics.set(document.uri, [new vscode.Diagnostic(
        new vscode.Range(0, 0, 0, 1),
        `nano_cust を実行できません: ${result.error.message}`,
        vscode.DiagnosticSeverity.Error,
      )]);
      return;
    }
    diagnostics.set(document.uri, result.code === 0 ? [] : [diagnosticFromOutput(document, output)]);
  }

  function schedule(document) {
    const config = vscode.workspace.getConfiguration("nanoCust", document.uri);
    if (!config.get("checkOnChange", true) || document.languageId !== LANGUAGE_ID) {
      return;
    }
    clearTimeout(pending.get(document.uri.toString()));
    pending.set(document.uri.toString(), setTimeout(() => check(document), config.get("checkDelay", 500)));
  }

  context.subscriptions.push(
    diagnostics,
    vscode.commands.registerCommand("nanoCust.checkSyntax", () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        return check(editor.document);
      }
      return undefined;
    }),
    vscode.workspace.onDidOpenTextDocument(schedule),
    vscode.workspace.onDidChangeTextDocument((event) => schedule(event.document)),
    vscode.workspace.onDidSaveTextDocument((document) => check(document)),
    vscode.workspace.onDidCloseTextDocument((document) => diagnostics.delete(document.uri)),
  );

  for (const document of vscode.workspace.textDocuments) {
    schedule(document);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
