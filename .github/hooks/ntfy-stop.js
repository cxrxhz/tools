#!/usr/bin/env node
// ============================================================
// Copilot Agent Stop Hook — ntfy 推送通知
// 当 Copilot 会话结束时，VS Code 自动调用此脚本。
// 从 transcript_path 读取对话记录，提取 agent 的文字回复并推送。
// 参考文档: https://code.visualstudio.com/docs/copilot/customization/hooks
// ============================================================

const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ntfy 消息体最大约 4KB 可舒适显示，截断到安全长度
const MAX_MSG_LEN = 3500;

function stripJsonComments(text) {
    return text
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/^\s*\/\/.*$/gm, '')
        .replace(/,\s*([}\]])/g, '$1');
}

function readSettingsFile(settingsPath) {
    if (!settingsPath || !fs.existsSync(settingsPath)) {
        return {};
    }

    try {
        const raw = fs.readFileSync(settingsPath, 'utf8');
        const settings = JSON.parse(stripJsonComments(raw));
        const result = {};

        if (typeof settings['ntfyBridge.serverUrl'] === 'string') {
            result.serverUrl = settings['ntfyBridge.serverUrl'];
        }
        if (typeof settings['ntfyBridge.inputTopic'] === 'string') {
            result.inputTopic = settings['ntfyBridge.inputTopic'];
        }
        if (typeof settings['ntfyBridge.outputTopic'] === 'string') {
            result.outputTopic = settings['ntfyBridge.outputTopic'];
        }

        return result;
    } catch (err) {
        process.stderr.write('read settings failed: ' + err.message + '\n');
        return {};
    }
}

function getUserSettingsPath() {
    if (process.platform === 'win32' && process.env.APPDATA) {
        return path.join(process.env.APPDATA, 'Code', 'User', 'settings.json');
    }

    if (process.platform === 'darwin') {
        return path.join(os.homedir(), 'Library', 'Application Support', 'Code', 'User', 'settings.json');
    }

    return path.join(os.homedir(), '.config', 'Code', 'User', 'settings.json');
}

function readEffectiveSettings(cwd) {
    const userSettings = readSettingsFile(getUserSettingsPath());
    const workspaceSettings = cwd
        ? readSettingsFile(path.join(cwd, '.vscode', 'settings.json'))
        : {};

    return {
        ...userSettings,
        ...workspaceSettings
    };
}

function normalizeServerUrl(value) {
    const trimmed = String(value || 'https://ntfy.sh').trim();
    return trimmed.replace(/\/+$/, '');
}

/**
 * 从 transcript JSONL 文件中提取最后一轮 agent 的所有文字回复
 */
function extractLastReply(transcriptPath) {
    try {
        const content = fs.readFileSync(transcriptPath, 'utf8');
        const lines = content.trim().split('\n');

        // 从后往前收集最后一轮 assistant 的文字消息
        const msgs = [];
        let foundAssistant = false;

        for (let i = lines.length - 1; i >= 0; i--) {
            let obj;
            try { obj = JSON.parse(lines[i]); } catch (_) { continue; }

            if (obj.type === 'assistant.message' && obj.data && obj.data.content) {
                const text = obj.data.content.trim();
                if (text.length > 0) {
                    msgs.unshift(text);
                    foundAssistant = true;
                }
            }
            // 遇到用户消息时停止（只取最后一轮）
            if (foundAssistant && obj.type === 'user.message') {
                break;
            }
        }

        return msgs.join('\n\n') || '';
    } catch (err) {
        return '(无法读取对话记录: ' + err.message + ')';
    }
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
    let data = {};
    try { data = JSON.parse(input); } catch (_) { /* 忽略解析失败 */ }

    const workspaceSettings = readEffectiveSettings(data.cwd || process.cwd());
    const serverUrl = normalizeServerUrl(
        process.env.NTFY_SERVER_URL || workspaceSettings.serverUrl
    );
    const outputTopic = String(
        process.env.NTFY_TOPIC || workspaceSettings.outputTopic || ''
    ).trim();
    const inputTopic = String(workspaceSettings.inputTopic || '').trim();

    if (!outputTopic) {
        process.stdout.write(JSON.stringify({}));
        return;
    }

    if (inputTopic && inputTopic === outputTopic) {
        process.stdout.write(JSON.stringify({}));
        return;
    }

    const now = new Date();
    const timeStr = now.toLocaleString('zh-CN', { hour12: false });

    // 从 transcript 文件提取 agent 的最后回复
    let replyText = '';
    if (data.transcript_path) {
        replyText = extractLastReply(data.transcript_path);
    }

    // 截断过长的消息
    if (replyText.length > MAX_MSG_LEN) {
        replyText = replyText.substring(0, MAX_MSG_LEN) + '\n...(已截断)';
    }

    const title = 'Copilot 会话已结束 · ' + timeStr;
    const message = replyText || '(本轮无文字回复)';

    const payload = JSON.stringify({
        topic: outputTopic,
        title: title,
        message: message,
        tags: ['robot', 'white_check_mark']
    });

    const buf = Buffer.from(payload, 'utf8');
    const req = https.request(serverUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Content-Length': buf.length
        }
    }, (res) => {
        let body = '';
        res.on('data', (c) => { body += c; });
        res.on('end', () => {
            if (res.statusCode && res.statusCode >= 400) {
                process.stderr.write(`ntfy push failed: HTTP ${res.statusCode} ${body}`.trim() + '\n');
            }
            process.stdout.write(JSON.stringify({}));
        });
    });

    req.on('error', (err) => {
        process.stderr.write('ntfy push error: ' + err.message + '\n');
        process.stdout.write(JSON.stringify({}));
    });

    req.setTimeout(10000, () => {
        req.destroy();
        process.stdout.write(JSON.stringify({}));
    });

    req.write(buf);
    req.end();
});
