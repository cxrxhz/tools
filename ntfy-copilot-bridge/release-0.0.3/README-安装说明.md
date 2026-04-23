# Ntfy Copilot Bridge 0.0.3 发布包说明

本发布包包含两部分：

1. `ntfy-copilot-bridge-0.0.3.vsix`
   VS Code 扩展本体，只负责手机消息输入到聊天。
2. `.github/hooks/ntfy-stop.js` 与 `.github/hooks/ntfy-stop.json`
   Copilot Stop hook，负责在会话结束后把本轮回复推送到 ntfy 输出频道。

当前 0.0.3 版本的 VSIX **没有把 hook 自动集成进插件内部**，所以发布时需要把这两个 hook 文件一并提供，或者指导用户复制到工作区根目录。

## 安装步骤

1. 在 VS Code 安装 `ntfy-copilot-bridge-0.0.3.vsix`
2. 将本包中的 `.github/hooks/` 整个目录复制到你的工作区根目录
3. 在 VS Code 设置中配置：
   - `ntfyBridge.inputTopic`: 手机 -> VS Code 输入频道
   - `ntfyBridge.outputTopic`: VS Code -> 手机完成推送频道
   - `ntfyBridge.serverUrl`: 可选，默认 `https://ntfy.sh`
4. 手机端需要订阅 **输出频道** 才能收到完成推送；仅向输入频道发消息并不代表已经订阅输出频道

## 当前默认用法

- 输入频道：`milkshakecopilot415263_in`
- 输出频道：`milkshakecopilot415263`

## 验证结论

本地已确认输出频道可收到服务端消息，说明 hook 的推送链路当前是通的。如果手机端没有看到消息，优先检查是否订阅了输出频道，而不是只使用了输入频道。