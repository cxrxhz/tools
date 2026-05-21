#!/usr/bin/env node
// ============================================================
// Copilot Agent Stop Hook v5 — ntfy 富内容推送
// 会话结束时：
//   1. 提取 agent 最后一轮文字回复
//   2. 检测回复中引用的图片文件路径
//   3. 保存结构化响应数据到 ~/.ntfy-bridge/latest.json
//      （触发 Extension 的 ResponseWatcher 异步上传图片）
//   4. 发送文字通知到 ntfy 输出频道
// ============================================================

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

// === 常量 ===
const MAX_MSG_LEN = 3500;
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp']);
const RESPONSE_DIR = path.join(os.homedir(), '.ntfy-bridge');

// === 设置文件读取 ===

function stripJsonComments(text) {
    return text
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/^\s*\/\/.*$/gm, '')
        .replace(/,\s*([}\]])/g, '$1');
}

function readSettingsFile(settingsPath) {
    if (!settingsPath || !fs.existsSync(settingsPath)) return {};
    try {
        var raw = fs.readFileSync(settingsPath, 'utf8');
        var s = JSON.parse(stripJsonComments(raw));
        var r = {};
        if (typeof s['ntfyBridge.serverUrl'] === 'string') r.serverUrl = s['ntfyBridge.serverUrl'];
        if (typeof s['ntfyBridge.inputTopic'] === 'string') r.inputTopic = s['ntfyBridge.inputTopic'];
        if (typeof s['ntfyBridge.outputTopic'] === 'string') r.outputTopic = s['ntfyBridge.outputTopic'];
        if (typeof s['ntfyBridge.forwardImages'] === 'boolean') r.forwardImages = s['ntfyBridge.forwardImages'];
        if (typeof s['ntfyBridge.viewerEnabled'] === 'boolean') r.viewerEnabled = s['ntfyBridge.viewerEnabled'];
        if (typeof s['ntfyBridge.viewerPort'] === 'number') r.viewerPort = s['ntfyBridge.viewerPort'];
        return r;
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
    var userSettings = readSettingsFile(getUserSettingsPath());
    var wsSettings = cwd ? readSettingsFile(path.join(cwd, '.vscode', 'settings.json')) : {};
    return Object.assign({}, userSettings, wsSettings);
}

function normalizeServerUrl(value) {
    return String(value || 'https://ntfy.sh').trim().replace(/\/+$/, '');
}

function getProto(url) {
    return url.startsWith('https') ? https : http;
}

// === 图片路径检测 ===

function detectImagesFromText(text, cwd) {
    var found = new Set();
    var m;

    // Markdown 图片引用 ![alt](path)
    var mdRe = /!\[[^\]]*\]\(([^)]+)\)/g;
    while ((m = mdRe.exec(text)) !== null) found.add(m[1]);

    // Windows 绝对路径
    var winRe = /[A-Za-z]:\\[\w\-.\\/]+\.(?:png|jpg|jpeg|gif|svg|webp|bmp)/gi;
    while ((m = winRe.exec(text)) !== null) found.add(m[0]);

    // Unix 绝对路径
    var unixRe = /\/[\w\-./]+\.(?:png|jpg|jpeg|gif|svg|webp|bmp)/gi;
    while ((m = unixRe.exec(text)) !== null) found.add(m[0]);

    // 相对路径
    var relRe = /(?:\.\/|[\w][\w\-]*\/)[\w\-./\\]+\.(?:png|jpg|jpeg|gif|svg|webp|bmp)/gi;
    while ((m = relRe.exec(text)) !== null) found.add(m[0]);

    // 解析为绝对路径并验证存在
    var valid = [];
    for (var p of found) {
        var abs = path.isAbsolute(p) ? p : (cwd ? path.resolve(cwd, p) : null);
        if (!abs) continue;
        abs = path.normalize(abs);
        if (fs.existsSync(abs) && IMAGE_EXTS.has(path.extname(abs).toLowerCase())) {
            valid.push(abs);
        }
    }
    return valid;
}

function detectImagesFromTranscript(lines, cwd) {
    var found = new Set();
    for (var i = 0; i < lines.length; i++) {
        var obj;
        try { obj = JSON.parse(lines[i]); } catch (_) { continue; }
        var jsonStr = JSON.stringify(obj);
        var re = /(?:filePath|file_path|path|imagePath|image_path)["':\s]+["']?([^"'\s,}]+\.(?:png|jpg|jpeg|gif|svg|webp|bmp))/gi;
        var m;
        while ((m = re.exec(jsonStr)) !== null) {
            var p = m[1];
            var abs = path.isAbsolute(p) ? p : (cwd ? path.resolve(cwd, p) : null);
            if (!abs) continue;
            abs = path.normalize(abs);
            if (fs.existsSync(abs) && IMAGE_EXTS.has(path.extname(abs).toLowerCase())) {
                found.add(abs);
            }
        }
    }
    return Array.from(found);
}

// === Transcript 解析 ===

function extractLastReply(transcriptPath) {
    try {
        var content = fs.readFileSync(transcriptPath, 'utf8');
        var lines = content.trim().split('\n');
        var msgs = [];
        var foundAssistant = false;

        for (var i = lines.length - 1; i >= 0; i--) {
            var obj;
            try { obj = JSON.parse(lines[i]); } catch (_) { continue; }
            if (obj.type === 'assistant.message' && obj.data && obj.data.content) {
                var text = obj.data.content.trim();
                if (text.length > 0) {
                    msgs.unshift(text);
                    foundAssistant = true;
                }
            }
            if (foundAssistant && obj.type === 'user.message') break;
        }

        return { text: msgs.join('\n\n') || '', lines: lines };
    } catch (err) {
        return { text: '(无法读取对话记录: ' + err.message + ')', lines: [] };
    }
}

// === 保存响应数据 ===

function saveResponseData(text, images, cwd) {
    try {
        if (!fs.existsSync(RESPONSE_DIR)) {
            fs.mkdirSync(RESPONSE_DIR, { recursive: true });
        }
        var data = {
            timestamp: Date.now(),
            timeStr: new Date().toLocaleString('zh-CN', { hour12: false }),
            text: text,
            images: images.map(function(p) {
                return {
                    absPath: p,
                    filename: path.basename(p),
                    ext: path.extname(p).toLowerCase()
                };
            }),
            cwd: cwd || ''
        };
        fs.writeFileSync(
            path.join(RESPONSE_DIR, 'latest.json'),
            JSON.stringify(data, null, 2),
            'utf8'
        );
    } catch (err) {
        process.stderr.write('save response failed: ' + err.message + '\n');
    }
}

// === ntfy 文字推送 ===

function sendTextPush(serverUrl, outputTopic, title, message, actions) {
    return new Promise(function(resolve, reject) {
        var payload = {
            topic: outputTopic,
            title: title,
            message: message,
            tags: ['robot', 'white_check_mark']
        };
        if (actions && actions.length > 0) payload.actions = actions;

        var buf = Buffer.from(JSON.stringify(payload), 'utf8');
        var proto = getProto(serverUrl);

        var req = proto.request(serverUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': buf.length
            }
        }, function(res) {
            var body = '';
            res.on('data', function(c) { body += c; });
            res.on('end', function() {
                if (res.statusCode >= 400) {
                    reject(new Error('HTTP ' + res.statusCode + ' ' + body));
                } else {
                    resolve();
                }
            });
        });

        req.on('error', reject);
        req.setTimeout(10000, function() { req.destroy(); reject(new Error('timeout')); });
        req.write(buf);
        req.end();
    });
}

// === 主流程 ===

var input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', function(chunk) { input += chunk; });
process.stdin.on('end', function() {
    var data = {};
    try { data = JSON.parse(input); } catch (_) { /* ignore */ }

    var cwd = data.cwd || process.cwd();
    var settings = readEffectiveSettings(cwd);
    var serverUrl = normalizeServerUrl(process.env.NTFY_SERVER_URL || settings.serverUrl);
    var outputTopic = String(process.env.NTFY_TOPIC || settings.outputTopic || '').trim();
    var inputTopic = String(settings.inputTopic || '').trim();
    var forwardImages = settings.forwardImages !== false;
    var viewerEnabled = settings.viewerEnabled === true;
    var viewerPort = settings.viewerPort || 19199;

    if (!outputTopic) {
        process.stdout.write(JSON.stringify({}));
        return;
    }
    if (inputTopic && inputTopic === outputTopic) {
        process.stdout.write(JSON.stringify({}));
        return;
    }

    // 1. 提取文字回复
    var reply = data.transcript_path
        ? extractLastReply(data.transcript_path)
        : { text: '', lines: [] };

    // 2. 检测图片文件
    var images = [];
    if (forwardImages && reply.text) {
        var textImages = detectImagesFromText(reply.text, cwd);
        var toolImages = detectImagesFromTranscript(reply.lines, cwd);
        var allSet = new Set(textImages.concat(toolImages));
        images = Array.from(allSet);
    }

    // 3. 保存响应数据（触发 Extension ResponseWatcher 上传图片 + Viewer 更新）
    saveResponseData(reply.text, images, cwd);

    // 4. 发送文字通知
    var now = new Date();
    var timeStr = now.toLocaleString('zh-CN', { hour12: false });
    var title = 'Copilot 会话已结束 · ' + timeStr;

    var textMessage = reply.text || '(本轮无文字回复)';
    if (images.length > 0) {
        textMessage += '\n\n📎 包含 ' + images.length + ' 张图片（随后发送）';
    }
    if (textMessage.length > MAX_MSG_LEN) {
        textMessage = textMessage.substring(0, MAX_MSG_LEN) + '\n...(已截断)';
    }

    // 构建 action 按钮
    var actions = [];
    if (viewerEnabled) {
        actions.push({
            action: 'view',
            label: '查看完整回复',
            url: 'http://127.0.0.1:' + viewerPort + '/'
        });
    }

    sendTextPush(serverUrl, outputTopic, title, textMessage, actions)
        .then(function() { process.stdout.write(JSON.stringify({})); })
        .catch(function(err) {
            process.stderr.write('ntfy push error: ' + err.message + '\n');
            process.stdout.write(JSON.stringify({}));
        });
});
