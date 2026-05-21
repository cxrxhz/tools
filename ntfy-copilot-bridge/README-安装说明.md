# Ntfy Copilot Bridge 3.0.0 发布包说明

手机远程调用 Copilot/Codex 的完整方案：手机发消息 → VS Code 注入官方聊天 → 回复（含图片）推送回手机。

## 发布包内容

1. **ntfy-copilot-bridge-3.0.0.vsix** — VS Code 扩展本体
   - 监听 ntfy 输入频道，将手机消息注入 VS Code 聊天
   - 监听 stop hook 保存的响应数据，自动上传图片到 ntfy
   - 内置 Web 查看器（手机浏览器查看完整回复含图片）
2. **.github/hooks/ntfy-stop.js + ntfy-stop.json** — Copilot Stop Hook
   - 会话结束时提取文字回复 + 检测图片文件路径
   - 保存结构化数据到 `~/.ntfy-bridge/latest.json`
   - 发送文字通知到 ntfy 输出频道

## 安装步骤

1. 在 VS Code 安装 `ntfy-copilot-bridge-3.0.0.vsix`
2. 将 `.github/hooks/` 目录复制到工作区根目录
3. 在 VS Code 设置中配置频道：
   - `ntfyBridge.inputTopic`: 手机 → VS Code 输入频道
   - `ntfyBridge.outputTopic`: VS Code → 手机推送频道
   - `ntfyBridge.serverUrl`: 可选，默认 `https://ntfy.sh`
   - `ntfyBridge.defaultTarget`: 可选，未显式指定时默认发给谁

## 新增配置项（3.0.0）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ntfyBridge.defaultTarget` | `auto` | 手机消息默认目标。`auto` = 发到当前激活聊天，`copilot` / `codex` = 自动补目标前缀 |
| `ntfyBridge.copilotMention` | `@copilot` | 发给 Copilot 时自动加的前缀；若你的 participant 名称不同，在这里改 |
| `ntfyBridge.codexMention` | `@codex` | 发给 Codex 时自动加的前缀；若你的 participant 名称不同，在这里改 |
| `ntfyBridge.forwardImages` | `true` | 自动将回复中引用的图片作为 ntfy 附件上传 |
| `ntfyBridge.viewerEnabled` | `false` | 启用本地 Web 查看器 |
| `ntfyBridge.viewerPort` | `19199` | Web 查看器端口 |
| `ntfyBridge.viewerHost` | `0.0.0.0` | 查看器绑定地址（`0.0.0.0` = 局域网可访问） |

## 使用方式

### 基础：纯文字推送
手机安装 ntfy App → 订阅输出频道 → 向输入频道发消息 → 收到回复通知。

### 输入路由：从手机指定 Copilot 或 Codex
如果你同时装了 Copilot 和 Codex，桥接层不会去猜“当前到底要发给谁”，而是按手机消息里的显式路由来处理。

支持两种方式：
- 单条消息指定目标：`/copilot 帮我解释这个函数`、`/codex 帮我改这个 bug`
- 先切换默认目标，再连续发消息：`/target codex`、`/target copilot`、`/target auto`

说明：
- `auto` 表示回到旧行为，发给当前激活的聊天窗口。
- `copilot` / `codex` 会自动在注入文本前加上 `ntfyBridge.copilotMention` 或 `ntfyBridge.codexMention`。
- 如果你的环境里实际 participant 名称不是 `@copilot` 或 `@codex`，把这两个配置改成真实前缀即可。

### 进阶：图片转发
当 Copilot 回复中引用了图片文件路径（如生成的图表），stop hook 自动检测并记录。
Extension 的 ResponseWatcher 监听变化后，将图片作为 ntfy 附件逐张上传到手机。

### 高级：Web 查看器
设置 `ntfyBridge.viewerEnabled: true` 后，Extension 启动本地 HTTP 服务。
手机浏览器访问 `http://<电脑IP>:19199/` 可查看：
- Markdown 渲染的完整回复
- 所有图片附件（原图质量）
- 3 秒自动刷新

需要手机和电脑在同一局域网，或通过 Tailscale 等虚拟局域网连接。

## 数据流

```
手机 ntfy App → inputTopic → Extension 注入聊天 → Copilot 处理
                                                      ↓
手机 ntfy App ← outputTopic ← Stop Hook 提取回复+图片 ← 会话结束
                                    ↓
                          ~/.ntfy-bridge/latest.json
                                    ↓
                     Extension ResponseWatcher 上传图片
                                    ↓
                        Web Viewer (手机浏览器)
```