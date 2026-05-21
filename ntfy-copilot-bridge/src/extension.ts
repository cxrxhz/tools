import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// ============================================================
// Ntfy Copilot Bridge v6 — 富内容转发 + 输入路由
// 功能：
//   1. 监听 ntfy 输入频道，将手机消息注入 VS Code 聊天
//   2. 监听 stop hook 保存的响应数据，自动上传图片到 ntfy
//   3. 本地 Web 查看器，手机浏览器查看完整回复含图片
//   4. 手机端可显式指定 Copilot / Codex 目标
//
// 【防循环设计】物理隔离双 topic：
//   发送（hook -> 手机）：ntfyBridge.outputTopic
//   接收（手机 -> VS Code）：ntfyBridge.inputTopic
// ============================================================

const BUILD_ID = '2026-04-24-input-routing-v6';
const RECONNECT_DELAY_MS = 5000;
const MIN_MSG_INTERVAL_MS = 3000;
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp']);
const RESPONSE_DIR = path.join(os.homedir(), '.ntfy-bridge');
const RESPONSE_FILE = path.join(RESPONSE_DIR, 'latest.json');

function normalizeServerUrl(value: string | undefined): string {
    const trimmed = (value || 'https://ntfy.sh').trim();
    return trimmed.replace(/\/+$/, '');
}

function getProtocol(url: string): typeof https | typeof http {
    return url.startsWith('https') ? https : http;
}

type ConnectionState = 'disconnected' | 'connecting' | 'connected';
type ChatTarget = 'auto' | 'copilot' | 'codex';

function normalizeChatTarget(value: string | undefined): ChatTarget {
    const normalized = String(value || 'auto').trim().toLowerCase();
    if (normalized === 'copilot' || normalized === 'codex') {
        return normalized;
    }
    return 'auto';
}

function describeChatTarget(target: ChatTarget): string {
    switch (target) {
        case 'copilot':
            return 'Copilot';
        case 'codex':
            return 'Codex';
        default:
            return '当前激活聊天';
    }
}

function parseTargetControlCommand(message: string): ChatTarget | undefined {
    const match = message.trim().match(/^\/(?:use|target)\s+(auto|copilot|codex)\s*$/i);
    return match ? normalizeChatTarget(match[1]) : undefined;
}

function parseMessageTarget(message: string): {
    target?: Exclude<ChatTarget, 'auto'>;
    text: string;
} {
    const trimmed = message.trim();
    const match = trimmed.match(/^(?:\/|@)?(copilot|codex)\s*(?::|：)?\s+([\s\S]*)$/i);
    if (!match) {
        return { text: trimmed };
    }
    return {
        target: normalizeChatTarget(match[1]) as Exclude<ChatTarget, 'auto'>,
        text: match[2].trim()
    };
}

type InjectionPlan = {
    routeSource: 'message' | 'session' | 'config' | 'active';
    target: ChatTarget;
    text: string;
    injected: string;
};

// ============================================================
// NtfyInputBridge: 手机消息注入 VS Code 聊天
// ============================================================
class NtfyInputBridge {
    private statusBar: vscode.StatusBarItem;
    private state: ConnectionState = 'disconnected';
    private wantListening = false;
    private request: any = null;
    private reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    private lastMessageTime = 0;
    private lineBuffer = '';
    private runtimeTargetOverride: ChatTarget | undefined;

    private handleDisconnected(reason: string) {
        this.log.appendLine(reason);
        this.request = null;
        if (this.state !== 'disconnected') {
            this.state = 'disconnected';
            this.updateStatusBar();
        }
        this.scheduleReconnect();
    }

    constructor(
        private context: vscode.ExtensionContext,
        private log: vscode.OutputChannel
    ) {
        this.statusBar = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right, 100
        );
        this.statusBar.command = 'ntfy-bridge.toggle';
        this.updateStatusBar();
        this.statusBar.show();
    }

    private get configuration(): vscode.WorkspaceConfiguration {
        return vscode.workspace.getConfiguration('ntfyBridge');
    }

    get serverUrl(): string {
        return normalizeServerUrl(
            this.configuration.get<string>('serverUrl', 'https://ntfy.sh')
        );
    }

    get inputTopic(): string {
        return this.configuration.get<string>('inputTopic', '').trim();
    }

    get outputTopic(): string {
        return this.configuration.get<string>('outputTopic', '').trim();
    }

    get defaultTarget(): ChatTarget {
        return normalizeChatTarget(this.configuration.get<string>('defaultTarget', 'auto'));
    }

    get copilotMention(): string {
        return this.configuration.get<string>('copilotMention', '@copilot').trim();
    }

    get codexMention(): string {
        return this.configuration.get<string>('codexMention', '@codex').trim();
    }

    private get effectiveTarget(): ChatTarget {
        return this.runtimeTargetOverride ?? this.defaultTarget;
    }

    private getConfigurationError(): string | undefined {
        if (!this.inputTopic) {
            return '请先配置 ntfyBridge.inputTopic';
        }
        if (this.outputTopic && this.inputTopic === this.outputTopic) {
            return 'inputTopic 与 outputTopic 不能相同，否则可能形成循环';
        }
        return undefined;
    }

    private updateStatusBar() {
        switch (this.state) {
            case 'disconnected':
                this.statusBar.text = '$(debug-disconnect) Ntfy';
                this.statusBar.tooltip =
                    'Ntfy Bridge — 已断开（点击切换） | 目标: ' +
                    describeChatTarget(this.effectiveTarget);
                break;
            case 'connecting':
                this.statusBar.text = '$(sync~spin) Ntfy';
                this.statusBar.tooltip =
                    'Ntfy Bridge — 正在连接... | 目标: ' +
                    describeChatTarget(this.effectiveTarget);
                break;
            case 'connected':
                this.statusBar.text = '$(radio-tower) Ntfy';
                this.statusBar.tooltip =
                    'Ntfy Bridge — 监听中: ' + this.inputTopic +
                    ' | 目标: ' + describeChatTarget(this.effectiveTarget);
                break;
        }
    }

    toggle() {
        if (this.wantListening) { this.stopListening(); }
        else { this.startListening(); }
    }

    startListening() {
        if (this.wantListening) {
            this.log.appendLine('[Input] 已在监听中');
            return;
        }
        const configError = this.getConfigurationError();
        if (configError) {
            this.log.appendLine('[Input][配置错误] ' + configError);
            vscode.window.showWarningMessage('Ntfy Bridge: ' + configError);
            return;
        }
        this.wantListening = true;
        this.log.appendLine(
            '[Input] 开始监听: ' + this.inputTopic +
            ' | server=' + this.serverUrl + ' | build=' + BUILD_ID
        );
        this.connect();
    }

    stopListening() {
        this.wantListening = false;
        this.disconnect();
        this.log.appendLine('[Input] 已停止监听');
    }

    private connect() {
        if (this.state !== 'disconnected') return;
        this.state = 'connecting';
        this.updateStatusBar();
        this.lineBuffer = '';

        const url = this.serverUrl + '/' + encodeURIComponent(this.inputTopic) + '/json';
        this.log.appendLine('[Input] GET ' + url);

        const proto = getProtocol(url);
        const req = proto.get(url, (res) => {
            if (res.statusCode !== 200) {
                this.handleDisconnected('[Input][错误] HTTP ' + res.statusCode);
                return;
            }
            this.state = 'connected';
            this.updateStatusBar();
            this.log.appendLine('[Input] 已连接，等待手机消息...');

            res.setEncoding('utf8');
            res.on('data', (chunk: string) => {
                this.lineBuffer += chunk;
                const lines = this.lineBuffer.split('\n');
                this.lineBuffer = lines.pop() || '';
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (trimmed) this.handleJsonLine(trimmed);
                }
            });
            res.on('end', () => this.handleDisconnected('[Input] 连接已关闭'));
            res.on('error', (err: Error) => this.handleDisconnected('[Input][流错误] ' + err.message));
            res.on('close', () => {
                if (this.wantListening && this.state === 'connected') {
                    this.handleDisconnected('[Input] 连接已关闭');
                }
            });
        });
        req.on('error', (err: Error) => this.handleDisconnected('[Input][连接错误] ' + err.message));
        this.request = req;
    }

    private disconnect() {
        if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = undefined; }
        if (this.request) { this.request.destroy(); this.request = null; }
        this.state = 'disconnected';
        this.updateStatusBar();
    }

    private scheduleReconnect() {
        if (!this.wantListening || this.reconnectTimer) return;
        this.log.appendLine('[Input] ' + (RECONNECT_DELAY_MS / 1000) + '秒后重连...');
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = undefined;
            if (this.wantListening) this.connect();
        }, RECONNECT_DELAY_MS);
    }

    private handleJsonLine(line: string) {
        let msg: any;
        try { msg = JSON.parse(line); } catch { return; }
        if (msg.event !== 'message') return;
        if (!msg.message || typeof msg.message !== 'string') return;
        const text = msg.message.trim();
        if (text.length === 0) return;

        const controlTarget = parseTargetControlCommand(text);
        if (controlTarget) {
            this.runtimeTargetOverride = controlTarget;
            this.updateStatusBar();
            this.log.appendLine(
                '[Input][路由] 默认目标已切换为: ' + describeChatTarget(controlTarget)
            );
            void vscode.window.showInformationMessage(
                'Ntfy Bridge: 默认目标切换为 ' + describeChatTarget(controlTarget)
            );
            return;
        }

        const now = Date.now();
        if (now - this.lastMessageTime < MIN_MSG_INTERVAL_MS) {
            this.log.appendLine('[Input][限流] 忽略: ' + text.substring(0, 50));
            return;
        }
        this.lastMessageTime = now;
        const plan = this.buildInjectionPlan(text);
        if (!plan.text) {
            this.log.appendLine('[Input][忽略] 路由前缀后消息为空');
            return;
        }
        this.log.appendLine(
            '[Input][收到] ' + plan.text.substring(0, 100) +
            ' | 目标=' + describeChatTarget(plan.target) +
            ' | 来源=' + plan.routeSource
        );
        this.injectToChat(plan);
    }

    private buildInjectionPlan(message: string): InjectionPlan {
        const parsed = parseMessageTarget(message);
        const target = parsed.target ?? this.effectiveTarget;
        const routeSource: InjectionPlan['routeSource'] = parsed.target
            ? 'message'
            : this.runtimeTargetOverride !== undefined
                ? 'session'
                : this.defaultTarget !== 'auto'
                    ? 'config'
                    : 'active';
        const text = parsed.text.trim();

        return {
            routeSource,
            target,
            text,
            injected: this.applyTargetPrefix(text, target)
        };
    }

    private applyTargetPrefix(message: string, target: ChatTarget): string {
        const trimmed = message.trim();
        if (!trimmed || target === 'auto') {
            return trimmed;
        }

        const mention = target === 'copilot'
            ? this.copilotMention
            : this.codexMention;
        if (!mention) {
            this.log.appendLine(
                '[Input][路由] ' + describeChatTarget(target) +
                ' 未配置前缀，回退到原始消息'
            );
            return trimmed;
        }

        const mentionLower = mention.toLowerCase();
        const trimmedLower = trimmed.toLowerCase();
        if (trimmedLower === mentionLower || trimmedLower.startsWith(mentionLower + ' ')) {
            return trimmed;
        }
        return mention + ' ' + trimmed;
    }

    private async injectToChat(plan: InjectionPlan) {
        try {
            await vscode.commands.executeCommand(
                'workbench.action.chat.open',
                { query: plan.injected, isPartialQuery: false }
            );
            this.log.appendLine(
                '[Input] 已注入聊天 | 目标=' + describeChatTarget(plan.target)
            );
        } catch (err: any) {
            this.log.appendLine('[Input][注入失败] ' + (err?.message || err));
            try {
                await vscode.commands.executeCommand(
                    'workbench.action.chat.open',
                    { query: plan.injected, isPartialQuery: true }
                );
                await vscode.commands.executeCommand(
                    'workbench.action.chat.acceptInput'
                );
                this.log.appendLine(
                    '[Input] 备用注入成功 | 目标=' + describeChatTarget(plan.target)
                );
            } catch (err2: any) {
                this.log.appendLine('[Input][备用失败] ' + (err2?.message || err2));
            }
        }
    }

    dispose() {
        this.stopListening();
        this.statusBar.dispose();
    }
}

// ============================================================
// ResponseWatcher: 监听 stop hook 保存的响应数据，自动上传图片
// ============================================================
class ResponseWatcher {
    private watcher: fs.FSWatcher | undefined;
    private lastProcessedTimestamp = 0;
    private debounceTimer: ReturnType<typeof setTimeout> | undefined;

    constructor(private log: vscode.OutputChannel) {}

    start() {
        try {
            if (!fs.existsSync(RESPONSE_DIR)) {
                fs.mkdirSync(RESPONSE_DIR, { recursive: true });
            }
            this.watcher = fs.watch(RESPONSE_DIR, (_eventType, filename) => {
                if (filename === 'latest.json') {
                    if (this.debounceTimer) clearTimeout(this.debounceTimer);
                    this.debounceTimer = setTimeout(() => this.processResponse(), 800);
                }
            });
            this.log.appendLine('[Watcher] 已开始监听 ' + RESPONSE_DIR);
        } catch (err: any) {
            this.log.appendLine('[Watcher] 监听失败: ' + err.message);
        }
    }

    private async processResponse() {
        try {
            const raw = fs.readFileSync(RESPONSE_FILE, 'utf8');
            const data = JSON.parse(raw);

            if (!data.timestamp || data.timestamp <= this.lastProcessedTimestamp) return;
            this.lastProcessedTimestamp = data.timestamp;

            if (!data.images || data.images.length === 0) return;

            const config = vscode.workspace.getConfiguration('ntfyBridge');
            if (config.get<boolean>('forwardImages') === false) return;

            const serverUrl = normalizeServerUrl(config.get<string>('serverUrl'));
            const outputTopic = config.get<string>('outputTopic', '').trim();
            if (!outputTopic) return;

            this.log.appendLine('[Watcher] 检测到 ' + data.images.length + ' 张图片，开始上传');

            for (const img of data.images) {
                if (!img.absPath || !fs.existsSync(img.absPath)) {
                    this.log.appendLine('[Watcher] 文件不存在: ' + (img.absPath || '(空)'));
                    continue;
                }
                try {
                    await this.uploadImage(serverUrl, outputTopic, img.absPath);
                    this.log.appendLine('[Watcher] 上传成功: ' + img.filename);
                } catch (err: any) {
                    this.log.appendLine('[Watcher] 上传失败: ' + img.filename + ' - ' + err.message);
                }
            }
        } catch {
            // 文件可能正在写入，静默忽略
        }
    }

    private uploadImage(serverUrl: string, topic: string, imagePath: string): Promise<void> {
        return new Promise((resolve, reject) => {
            let fileBuffer: Buffer;
            try {
                fileBuffer = fs.readFileSync(imagePath);
            } catch (err: any) {
                reject(new Error('读取失败: ' + err.message));
                return;
            }

            const filename = path.basename(imagePath);
            const ext = path.extname(filename).toLowerCase();
            const mimeMap: Record<string, string> = {
                '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.gif': 'image/gif', '.svg': 'image/svg+xml',
                '.webp': 'image/webp', '.bmp': 'image/bmp'
            };

            const fullUrl = serverUrl + '/' + encodeURIComponent(topic);
            const urlObj = new URL(fullUrl);
            const proto = getProtocol(fullUrl);

            const req = proto.request(urlObj, {
                method: 'PUT',
                headers: {
                    'Content-Type': mimeMap[ext] || 'application/octet-stream',
                    'Content-Length': fileBuffer.length,
                    'Filename': filename,
                    'Title': filename,
                    'Tags': 'framed_picture'
                }
            }, (res) => {
                let body = '';
                res.on('data', (c: string) => body += c);
                res.on('end', () => {
                    if (res.statusCode && res.statusCode >= 400) {
                        reject(new Error('HTTP ' + res.statusCode + ': ' + body));
                    } else {
                        resolve();
                    }
                });
            });

            req.on('error', reject);
            req.setTimeout(30000, () => { req.destroy(); reject(new Error('上传超时')); });
            req.write(fileBuffer);
            req.end();
        });
    }

    dispose() {
        if (this.debounceTimer) clearTimeout(this.debounceTimer);
        this.watcher?.close();
    }
}

// ============================================================
// ViewerServer: 本地 HTTP 服务器，手机浏览器查看完整回复含图片
// ============================================================
class ViewerServer {
    private server: http.Server | undefined;

    constructor(private log: vscode.OutputChannel) {}

    start(port: number, host: string) {
        this.server = http.createServer((req, res) => this.handleRequest(req, res));
        this.server.listen(port, host, () => {
            this.log.appendLine('[Viewer] 已启动: http://' + host + ':' + port + '/');
        });
        this.server.on('error', (err: any) => {
            if (err.code === 'EADDRINUSE') {
                this.log.appendLine('[Viewer] 端口 ' + port + ' 被占用，未启动');
            } else {
                this.log.appendLine('[Viewer] 启动失败: ' + err.message);
            }
        });
    }

    private handleRequest(req: http.IncomingMessage, res: http.ServerResponse) {
        const reqUrl = new URL(req.url || '/', 'http://' + (req.headers.host || 'localhost'));

        if (reqUrl.pathname === '/' || reqUrl.pathname === '/index.html') {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(generateViewerHtml());
        } else if (reqUrl.pathname === '/api/latest') {
            this.serveLatestJson(res);
        } else if (reqUrl.pathname === '/file') {
            this.serveImage(res, reqUrl.searchParams.get('p') || '');
        } else {
            res.writeHead(404);
            res.end('Not Found');
        }
    }

    private serveLatestJson(res: http.ServerResponse) {
        try {
            if (fs.existsSync(RESPONSE_FILE)) {
                const data = fs.readFileSync(RESPONSE_FILE, 'utf8');
                res.writeHead(200, {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                });
                res.end(data);
            } else {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end('{"text":"","images":[],"timestamp":0}');
            }
        } catch {
            res.writeHead(500);
            res.end('Internal Error');
        }
    }

    private serveImage(res: http.ServerResponse, filePath: string) {
        if (!filePath) { res.writeHead(400); res.end('Missing path'); return; }

        const normalized = path.normalize(filePath);
        const ext = path.extname(normalized).toLowerCase();

        // 安全: 只允许图片类型
        if (!IMAGE_EXTENSIONS.has(ext)) {
            res.writeHead(403); res.end('Forbidden'); return;
        }

        // 安全: 只允许 latest.json 中引用的图片（防止任意文件读取）
        try {
            const responseData = JSON.parse(fs.readFileSync(RESPONSE_FILE, 'utf8'));
            const allowedPaths: string[] = (responseData.images || []).map(
                (img: any) => path.normalize(img.absPath)
            );
            if (!allowedPaths.includes(normalized)) {
                res.writeHead(403); res.end('Forbidden'); return;
            }
        } catch {
            res.writeHead(403); res.end('Forbidden'); return;
        }

        if (!fs.existsSync(normalized)) {
            res.writeHead(404); res.end('Not found'); return;
        }

        const mimeMap: Record<string, string> = {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.svg': 'image/svg+xml',
            '.webp': 'image/webp', '.bmp': 'image/bmp'
        };

        try {
            const data = fs.readFileSync(normalized);
            res.writeHead(200, {
                'Content-Type': mimeMap[ext] || 'application/octet-stream',
                'Content-Length': data.length,
                'Cache-Control': 'public, max-age=60'
            });
            res.end(data);
        } catch {
            res.writeHead(500); res.end('Error');
        }
    }

    dispose() {
        this.server?.close();
    }
}

// ============================================================
// Viewer HTML — 手机端暗色主题，Markdown 渲染，自动刷新
// ============================================================
function generateViewerHtml(): string {
    return [
        '<!DOCTYPE html><html lang="zh-CN"><head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=5.0">',
        '<title>Copilot Viewer</title>',
        '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"><\/script>',
        '<style>',
        '*{margin:0;padding:0;box-sizing:border-box}',
        ':root{--bg:#0d1117;--sf:#161b22;--bd:#30363d;--tx:#c9d1d9;--mt:#8b949e;--ac:#58a6ff;--cb:#1c2128}',
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;',
        'background:var(--bg);color:var(--tx);line-height:1.6;padding:12px;max-width:860px;margin:0 auto}',
        '.hd{display:flex;justify-content:space-between;align-items:center;padding-bottom:10px;',
        'border-bottom:1px solid var(--bd);margin-bottom:14px}',
        '.hd h1{font-size:17px;color:var(--ac)}.hd .t{font-size:11px;color:var(--mt)}',
        '.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;',
        'background:#1f6feb33;color:var(--ac);margin-bottom:10px}',
        '.md{font-size:14px;word-wrap:break-word}',
        '.md h1,.md h2,.md h3{color:var(--ac);margin:14px 0 6px}',
        '.md h1{font-size:20px}.md h2{font-size:17px}.md h3{font-size:15px}',
        '.md p{margin:6px 0}',
        '.md code{background:var(--cb);padding:2px 5px;border-radius:3px;font-size:12px;',
        'font-family:"Cascadia Code",Consolas,monospace}',
        '.md pre{background:var(--cb);padding:10px;border-radius:6px;overflow-x:auto;',
        'margin:10px 0;border:1px solid var(--bd)}',
        '.md pre code{background:none;padding:0;font-size:12px}',
        '.md a{color:var(--ac)}.md img{max-width:100%;border-radius:6px;margin:8px 0}',
        '.md ul,.md ol{padding-left:20px;margin:6px 0}',
        '.md blockquote{border-left:3px solid var(--bd);padding-left:12px;color:var(--mt);margin:8px 0}',
        '.md table{border-collapse:collapse;margin:10px 0;width:100%}',
        '.md th,.md td{border:1px solid var(--bd);padding:6px 10px;text-align:left;font-size:13px}',
        '.md th{background:var(--sf)}',
        '.md strong{color:#e6edf3}',
        '.ims{margin-top:14px}.ims h2{font-size:13px;color:var(--mt);margin-bottom:6px}',
        '.ic{margin-bottom:10px;border-radius:6px;overflow:hidden;border:1px solid var(--bd)}',
        '.ic img{width:100%;display:block}',
        '.ic .lb{padding:4px 8px;background:var(--sf);font-size:11px;color:var(--mt)}',
        '.empty{text-align:center;padding:30px;color:var(--mt)}',
        '.ft{text-align:center;padding:10px;font-size:11px;color:var(--mt);margin-top:16px;',
        'border-top:1px solid var(--bd);cursor:pointer}',
        '</style></head><body>',
        '<div class="hd"><h1>Copilot Viewer</h1><span class="t" id="tm"></span></div>',
        '<div class="badge" id="st">Loading...</div>',
        '<div class="md" id="ct"></div>',
        '<div class="ims" id="im"></div>',
        '<div class="ft" id="ft" onclick="load()">Tap to refresh | auto-refresh 3s</div>',
        '<script>',
        'function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}',
        'var lastTs=0;',
        'function load(){',
        '  fetch("/api/latest").then(function(r){return r.json()}).then(function(d){',
        '    if(d.timestamp===lastTs)return;lastTs=d.timestamp;',
        '    document.getElementById("tm").textContent=d.timeStr||"";',
        '    document.getElementById("st").textContent=d.timestamp?"Latest":"Waiting...";',
        '    var c=document.getElementById("ct");',
        '    if(d.text){',
        '      if(typeof marked!=="undefined"){try{c.innerHTML=marked.parse(d.text)}catch(e){c.textContent=d.text}}',
        '      else{c.textContent=d.text}',
        '    }else{c.innerHTML="<div class=\\"empty\\">No response yet</div>"}',
        '    var im=document.getElementById("im");',
        '    if(d.images&&d.images.length>0){',
        '      var h="<h2>Attachments ("+d.images.length+")</h2>";',
        '      d.images.forEach(function(i){',
        '        h+="<div class=\\"ic\\"><img src=\\"/file?p="+encodeURIComponent(i.absPath)+',
        '           "\\" loading=\\"lazy\\"><div class=\\"lb\\">"+esc(i.filename)+"</div></div>"',
        '      });im.innerHTML=h',
        '    }else{im.innerHTML=""}',
        '  }).catch(function(){document.getElementById("st").textContent="Connection failed"})',
        '}',
        'load();setInterval(load,3000);',
        '<\/script></body></html>'
    ].join('\n');
}

// ============================================================
// 模块级变量 & 生命周期
// ============================================================
let bridge: NtfyInputBridge | undefined;
let responseWatcher: ResponseWatcher | undefined;
let viewer: ViewerServer | undefined;

export function activate(context: vscode.ExtensionContext) {
    const log = vscode.window.createOutputChannel('Ntfy Bridge');
    log.appendLine('[Main] activate ' + BUILD_ID);

    bridge = new NtfyInputBridge(context, log);

    // 响应数据监听器（始终运行，自动上传图片到 ntfy）
    responseWatcher = new ResponseWatcher(log);
    responseWatcher.start();

    // 根据配置启动 Web 查看器
    const config = vscode.workspace.getConfiguration('ntfyBridge');
    if (config.get<boolean>('viewerEnabled', false)) {
        viewer = new ViewerServer(log);
        viewer.start(
            config.get<number>('viewerPort', 19199),
            config.get<string>('viewerHost', '0.0.0.0')
        );
    }

    context.subscriptions.push(
        vscode.commands.registerCommand('ntfy-bridge.toggle', () => bridge?.toggle()),
        vscode.commands.registerCommand('ntfy-bridge.start', () => {
            bridge?.startListening();
            vscode.window.showInformationMessage(
                'Ntfy Bridge: 开始监听 ' + (bridge?.inputTopic || '')
            );
        }),
        vscode.commands.registerCommand('ntfy-bridge.stop', () => {
            bridge?.stopListening();
            vscode.window.showInformationMessage('Ntfy Bridge: 已停止监听');
        }),
        vscode.commands.registerCommand('ntfy-bridge.openViewer', () => {
            const port = config.get<number>('viewerPort', 19199);
            vscode.env.openExternal(vscode.Uri.parse('http://localhost:' + port + '/'));
        }),
        { dispose: () => {
            bridge?.dispose();
            responseWatcher?.dispose();
            viewer?.dispose();
            log.dispose();
        }}
    );

    if (config.get<boolean>('autoStart', false)) {
        bridge.startListening();
    }
}

export function deactivate() {
    bridge?.dispose();
    responseWatcher?.dispose();
    viewer?.dispose();
}
