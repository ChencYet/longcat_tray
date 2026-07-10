# LongCat 用量监控托盘小工具

实时显示 LongCat（`longcat.chat`）Token 用量情况的 Windows 托盘小工具，图标变色 + 右键菜单一目了然。

## ✨ 功能

- 🎨 **图标随余量变色** — 绿色（≥50%）→ 橙色（20~50%）→ 红色（<20%）→ 灰色（获取失败）
- 🔢 **图标显示剩余百分比** — 不需要悬停，直接看数字
- 💬 **悬浮 Tooltip** — 鼠标悬停查看剩余量 / 已消耗 / 预计可用天数
- 📊 **右键菜单直接看详情** — Token 余量、有效期、日均消耗、预计用尽时间、最后刷新时间，无需弹窗
- ⏱️ **可自定义刷新间隔** — 手动 / 1 / 5 / 15 / 30 / 60 分钟，自动保存
- 🔔 **用量预警** — 低于阈值弹出系统通知
- 🍪 **自动获取 Cookie** — 首次启动自动从 Chrome / Edge 读取登录态，无需手动复制
- ⚠️ **Cookie 失效通知** — 获取失败时弹出系统通知提示重新登录

## 📥 快速开始

### 下载 EXE（无需 Python）

👉 [📦 下载最新版](https://github.com/ChencYet/longcat_tray/releases/latest/download/LongCatUsage.exe)

下载 `LongCatUsage.exe`，放在一个文件夹里（目录里会有 `config.json`），双击运行。

首次启动会弹出 UAC 授权，点「是」即可自动从浏览器读取登录态。

### 从源码运行

```bash
git clone https://github.com/YOUR_USERNAME/longcat-tray.git
cd longcat-tray
pip install -r requirements.txt
python tray_app.py
```

## 🖱️ 托盘图标 & 菜单

```
剩余 45.3% / 100.0万
已消耗 54.7万 (54.7%)
有效期 2026-08-15
剩余 35天6小时
日均 1.23万
预计 10 天后用尽
刷新 14:32:01
------------------------------------
立即刷新
------------------------------------
刷新间隔 >
  ○ 仅手动刷新
  ● 5 分钟
  ○ 15 分钟
  ○ 30 分钟
  ○ 60 分钟
------------------------------------
退出
```

| 图标颜色 | 含义 |
|---------|------|
| 🟢 绿色数字 | 剩余 ≥ 50% |
| 🟠 橙色数字 | 剩余 20% ~ 50% |
| 🔴 红色数字 | 剩余 < 20% |
| ⚪ 灰色 `!` | 获取失败（Cookie 可能已失效） |

## 🍪 Cookie 机制

**自动获取**：首次启动请求管理员权限（UAC），从 Chrome 或 Edge 浏览器自动读取 `longcat.chat` 域名下的 Cookie，保存到 `config.json`，后续不再需要。

**Cookie 过期处理**：当 Cookie 失效时，图标变灰 + 弹出系统通知。你只需要在浏览器重新访问 `longcat.chat` 登录一下，然后右键托盘 → 立即刷新，即可恢复正常（不需要重启程序、不需要重新获取）。

> ⚠️ `config.json` 里的 Cookie 相当于你的登录凭证，**不要**把这个文件夹传到公开仓库。`.gitignore` 已排除 `config.json`。

## 📦 打包 EXE

```bash
pip install pyinstaller
pyinstaller LongCatUsage.spec
```

打包完成后在 `dist/LongCatUsage.exe` 找到可执行文件。`config.json` 需与 exe 放在同一目录。

## 🔧 开机自启

按 `Win+R`，输入 `shell:startup` 回车，把 `LongCatUsage.exe` 的快捷方式放进去即可。

## 🔩 技术栈

- Python 3.10+
- [pystray](https://github.com/moses-palmer/pystray) — 系统托盘
- [Pillow](https://python-pillow.org/) — 图标绘制
- [requests](https://requests.readthedocs.io/) — API 调用
- [browser-cookie3](https://github.com/borisbabic/browser_cookie3) — 浏览器 Cookie 读取
- [PyInstaller](https://pyinstaller.org/) — 打包为 EXE

## 📁 文件结构

```
longcat-tray/
├── tray_app.py            # 主程序（单文件，全部逻辑）
├── LongCatUsage.spec      # PyInstaller 打包配置
├── requirements.txt       # Python 依赖
├── config.json            # 配置文件（运行时自动生成）
└── .gitignore             # Git 忽略规则
```

## 🙋 FAQ

**Cookie 会过期吗？**
会。LongCat 的登录态一般能维持几天到几周不等。过期后重新在浏览器登录一下就行，不需要手动操作配置文件。

**支持哪些浏览器？**
Chrome 和 Edge 都支持。优先读取 Chrome，如果 Chrome 没找到则尝试 Edge。

**为什么首次启动要管理员权限？**
Windows 上 Chrome / Edge 正在运行时会锁定 Cookie 数据库文件，必须提升权限才能完成卷影复制（shadow copy）读取。仅在首次获取 Cookie 时需要，后续运行不再弹 UAC。

**运行日志在哪？**
`%USERPROFILE%\.longcat_tray\error.log`

**怎么卸载？**
退出托盘程序 + 删除程序文件夹即可。如设置了开机自启，记得从 `shell:startup` 删除快捷方式。
