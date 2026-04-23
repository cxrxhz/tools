import * as vscode from 'vscode';
import * as https from 'https';

// ============================================================
// Ntfy Copilot Bridge v4 — 手机消息注入模式
// 监听 ntfy 专用输入频道（_in），将手机消息注入到 VS Code 聊天。
//
// 【防循环设计】物理隔离双 topic：
//   发送（hook -> 手机）：ntfyBridge.outputTopic
//   接收（手机 -> VS Code）：ntfyBridge.inputTopic
//   两个频道必须不同，否则扩展会拒绝启动监听。
// ============================================================

const BUILD_ID = '2026-04-21-publish-cleanup-v1';
const RECONNECT_DELAY_MS = 5000;
const MIN_MSG_INTERVAL_MS = 3000;

function normalizeServerUrl(value: string | undefined): string {
    const trimmed = (value || 'https://ntfy.sh').trim();
    return trimmed.replace(/\/+$/, '');
}

type ConnectionState = 'disconnected' | 'connecting' | 'connected';

class NtfyInputBridge {
    private statusBar: vscode.StatusBarItem;
    private log: vscode.OutputChannel;
    private state: ConnectionState = 'disconnected';
    private wantListening = false;
    private request: any = null;
    private reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    private lastMessageTime = 0;
    private lineBuffer = '';

    private handleDisconnected(reason: string) {
        this.log.appendLine(reason);
        this.request = null;

        if (this.state !== 'disconnected') {
            this.state = 'disconnected';
            this.updateStatusBar();
        }

        this.scheduleReconnect();
    }

    constructor(private context: vscode.ExtensionContext) {
        this.log = vscode.window.createOutputChannel('Ntfy Input Bridge');
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

    private getConfigurationError(): string | undefined {
        if (!this.inputTopic) {
            return '请先配置 ntfyBridge.inputTopic';
        }
        if (this.outputTopic && this.inputTopic === this.outputTopic) {
            return 'ntfyBridge.inputTopic 与 ntfyBridge.outputTopic 不能相同，否则可能形成循环';
        }
        return undefined;
    }

    private updateStatusBar() {
        switch (this.state) {
            case 'disconnected':
                this.statusBar.text = '$(debug-disconnect) Ntfy';
                this.statusBar.tooltip = 'Ntfy Input Bridge — 点击开始监听；请先配置输入频道';
                break;
            case 'connecting':
                this.statusBar.text = '$(sync~spin) Ntfy';
                this.statusBar.tooltip = 'Ntfy Input Bridge — 正在连接...';
                break;
            case 'connected':
                this.statusBar.text = '$(radio-tower) Ntfy';
                this.statusBar.tooltip =
                    'Ntfy Input Bridge — 监听中: ' + this.inputTopic;
                break;
        }
    }

    toggle() {
        if (this.wantListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }

    startListening() {
        if (this.wantListening) {
            this.log.appendLine('[信息] 已在监听中');
            return;
        }

        const configError = this.getConfigurationError();
        if (configError) {
            this.log.appendLine(`[配置错误] ${configError}`);
            vscode.window.showWarningMessage(`Ntfy Bridge: ${configError}`);
            return;
        }

        this.wantListening = true;
        this.log.appendLine(
            `[启动] 开始监听 ntfy 输入频道: ${this.inputTopic} | server=${this.serverUrl} | build=${BUILD_ID}`
        );
        this.connect();
    }

    stopListening() {
        this.wantListening = false;
        this.disconnect();
        this.log.appendLine('[停止] 已停止监听');
    }

    private connect() {
        if (this.state !== 'disconnected') return;
        this.state = 'connecting';
        this.updateStatusBar();
        this.lineBuffer = '';

        // 使用 JSON stream（比 SSE 更简单可靠）
        const url = `${this.serverUrl}/${encodeURIComponent(this.inputTopic)}/json`;
        this.log.appendLine(`[连接] GET ${url}`);

        const req = https.get(url, (res) => {
            if (res.statusCode !== 200) {
                this.handleDisconnected(`[错误] HTTP ${res.statusCode}`);
                return;
            }

            this.state = 'connected';
            this.updateStatusBar();
            this.log.appendLine('[已连接] 等待手机消息...');

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

            res.on('end', () => {
                this.handleDisconnected('[断开] 连接已关闭');
            });

            res.on('error', (err: Error) => {
                this.handleDisconnected(`[流错误] ${err.message}`);
            });

            res.on('close', () => {
                if (this.wantListening && this.state === 'connected') {
                    this.handleDisconnected('[断开] 连接已关闭');
                }
            });
        });

        req.on('error', (err: Error) => {
            this.handleDisconnected(`[连接错误] ${err.message}`);
        });

        this.request = req;
    }

    private disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = undefined;
        }
        if (this.request) {
            this.request.destroy();
            this.request = null;
        }
        this.state = 'disconnected';
        this.updateStatusBar();
    }

    private scheduleReconnect() {
        if (!this.wantListening) return;
        if (this.reconnectTimer) return;

        this.log.appendLine(
            `[重连] ${RECONNECT_DELAY_MS / 1000}秒后重试...`
        );
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = undefined;
            if (this.wantListening) {
                this.connect();
            }
        }, RECONNECT_DELAY_MS);
    }

    private handleJsonLine(line: string) {
        let msg: any;
        try {
            msg = JSON.parse(line);
        } catch {
            return; // 忽略非 JSON 行
        }

        // 只处理 message 类型事件
        if (msg.event !== 'message') return;
        if (!msg.message || typeof msg.message !== 'string') return;

        const text = msg.message.trim();
        if (text.length === 0) return;

        // 限流
        const now = Date.now();
        if (now - this.lastMessageTime < MIN_MSG_INTERVAL_MS) {
            this.log.appendLine(
                `[限流] 消息间隔过短，忽略: ${text.substring(0, 50)}`
            );
            return;
        }
        this.lastMessageTime = now;

        this.log.appendLine(`[收到] ${text.substring(0, 100)}`);
        this.injectToChat(text);
    }

    private async injectToChat(message: string) {
        try {
            // 打开聊天面板并提交消息
            // isPartialQuery=false 表示自动提交
            await vscode.commands.executeCommand(
                'workbench.action.chat.open',
                { query: message, isPartialQuery: false }
            );
            this.log.appendLine('[注入] 已发送到聊天');
        } catch (err: any) {
            this.log.appendLine(`[注入失败] ${err?.message || err}`);
            // 备用方案：先设置输入框文本，再手动提交
            try {
                await vscode.commands.executeCommand(
                    'workbench.action.chat.open',
                    { query: message, isPartialQuery: true }
                );
                await vscode.commands.executeCommand(
                    'workbench.action.chat.acceptInput'
                );
                this.log.appendLine('[注入] 备用方案成功');
            } catch (err2: any) {
                this.log.appendLine(
                    `[注入失败-备用] ${err2?.message || err2}`
                );
            }
        }
    }

    dispose() {
        this.stopListening();
        this.statusBar.dispose();
        this.log.dispose();
    }
}

let bridge: NtfyInputBridge | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log(`[Ntfy Input Bridge] activate ${BUILD_ID}`);
    bridge = new NtfyInputBridge(context);

    context.subscriptions.push(
        vscode.commands.registerCommand('ntfy-bridge.toggle', () => {
            bridge?.toggle();
        }),
        vscode.commands.registerCommand('ntfy-bridge.start', () => {
            bridge?.startListening();
            vscode.window.showInformationMessage(
                `Ntfy Bridge: 开始监听 ${bridge?.inputTopic}`
            );
        }),
        vscode.commands.registerCommand('ntfy-bridge.stop', () => {
            bridge?.stopListening();
            vscode.window.showInformationMessage(
                'Ntfy Bridge: 已停止监听'
            );
        }),
        { dispose: () => bridge?.dispose() }
    );

    const autoStart = vscode.workspace
        .getConfiguration('ntfyBridge')
        .get<boolean>('autoStart', false);

    if (autoStart) {
        bridge.startListening();
    }
}

export function deactivate() {
    bridge?.dispose();
}
