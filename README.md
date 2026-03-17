# ChatHandy

基于 pywebview + Claude API 的智能灵巧手控制聊天界面。

用自然语言控制 LHandPro 灵巧手，支持手势识别、动作序列执行，同时提供日常 AI 对话能力。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![pywebview](https://img.shields.io/badge/pywebview-6.1-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 功能

- **自然语言控制**：说「握拳」「比耶」「点赞」直接驱动灵巧手
- **多手势序列**：「随机3个手势」自动按序执行
- **设备管理**：「启动灵巧手」初始化硬件，「关闭灵巧手」断开连接
- **AI 对话**：无关手势的消息走普通聊天
- **彩色 Emoji**：Edge WebView2 渲染，完整显示
- **设置界面**：API Key / Base URL / 模型 / System Prompt 可视化配置，保存到本地

## 截图

> 聊天界面 · 手势执行进度 · 设置弹窗

## 环境要求

- Windows 10/11（需要 Edge WebView2 Runtime，Win10 1803+ 通常已内置）
- Python 3.10+
- LHandPro 灵巧手 + CANFD 驱动（硬件可选，无硬件仍可使用 AI 对话）

## 安装

```bash
git clone https://github.com/sorrowfeng/ChatHandy.git
cd ChatHandy
pip install -r requirements.txt
```

## 配置

首次运行后点击右上角「设置」填写：

| 字段 | 说明 |
|------|------|
| API Key | MiniMax / Anthropic 的 API Key |
| Base URL | API 端点，如 `https://api.minimaxi.com/anthropic` |
| 模型 | 如 `MiniMax-M2.5-highspeed` |
| System Prompt | 默认已包含手势控制规则，可自定义 |

配置保存在本地 `config.json`（已加入 `.gitignore`，不会上传）。

## 运行

```bash
python main.py
```

## 使用示例

```
启动灵巧手          → 初始化硬件（约 5 秒）
握拳               → 执行握拳手势
先耶再点赞          → 依次执行两个手势
随机做三个手势       → AI 自由发挥，逐步执行
关闭灵巧手          → 断开硬件连接
你好              → 普通 AI 对话
```

## 项目结构

```
ChatHandy/
├── main.py                          # 入口，启动 pywebview 窗口
├── requirements.txt
├── config.json                      # 本地配置（gitignored）
├── chat/
│   ├── handler.py                   # AI 意图识别 + 对话历史
│   ├── runner.py                    # TCP IPC 客户端，控制灵巧手
│   ├── webview_app.py               # pywebview JS API 桥接层
│   ├── config.py                    # 配置读写
│   ├── settings_dialog.py           # 设置对话框（旧 customtkinter，备用）
│   ├── bubble.py                    # 消息气泡组件（旧 customtkinter，备用）
│   └── ui/
│       └── index.html               # 聊天 UI（HTML/CSS/JS）
├── hand/
│   └── server.py                    # LHandPro TCP 控制服务端
└── LHandProLib_CANFD_Test_python/   # 厂商硬件库
```

## 技术架构

```
用户输入
  ↓
pywebview JS → Python Api.send_message()
  ↓
ChatHandler → MiniMax/Anthropic API（意图识别）
  ↓
intent=gesture  → CommandRunner → TCP Socket → hand/server.py → LHandPro 硬件
intent=chat     → 直接返回 AI 回复
intent=start    → 后台线程启动 hand/server.py，完成后推送 JS 回调
```

## License

MIT
