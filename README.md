# LongCat 用量监控托盘小工具

实时显示 LongCat（`longcat.chat`）Token 用量情况的 Windows 托盘小工具，图标变色 + 右键菜单一目了然。

## ✨ 功能

- 🎨 **图标随余量变色** — 绿色（≥50%）→ 橙色（20~50%）→ 红色（<20%）→ 灰色（获取失败）
- 🔢 **图标显示剩余百分比** — 不需要悬停，直接看数字
- 💬 **悬浮 Tooltip** — 鼠标悬停查看剩余量 / 已消耗 / 预计可用天数
- 📊 **右键菜单直接看详情** — Token 余量、有效期、日均消耗、预计用尽时间、最后刷新时间
- ⏱️ **可自定义刷新间隔** — 手动 / 1 / 5 / 15 / 30 / 60 分钟，自动保存
- 🔔 **用量预警** — 低于阈值弹出系统通知
- 🍪 **Cookie 失效通知** — 获取失败时弹出系统通知提示重新登录

## 📥 快速开始

### 下载 EXE（无需 Python）

👉 [📦 下载最新版](https://github.com/ChencYet/longcat_tray/releases/latest/download/LongCatUsage.exe)

下载 `LongCatUsage.exe`，放在一个文件夹里（目录里会有 `config.json`），双击运行。

首次启动会提示你用记事本打开 `config.json`，填入 Cookie 后保存、重启程序即可。

### 从源码运行

```bash
git clone https://github.com/ChencYet/longcat_tray.git
cd longcat_tray
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
编辑 Cookie（记事本）
重新加载配置
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

## 🍪 Cookie 配置

### 首次配置

1. 双击运行 `LongCatUsage.exe`
2. 弹出提示 → 自动用记事本打开 `config.json`
3. 在浏览器登录 `longcat.chat` → F12 → Network → 任意请求 → 复制 Cookie 头
4. 粘贴到 `config.json` 的 `cookie` 字段，保存
5. 重新启动程序

### Cookie 过期更新

1. 在浏览器重新登录 `longcat.chat`
2. 右键托盘图标 → 「编辑 Cookie（记事本）」
3. 替换 `cookie` 字段，保存
4. 右键托盘图标 → 「重新加载配置」

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
会。LongCat 的登录态一般能维持几天到几周不等。过期后重新在浏览器登录一下，更新 `config.json` 里的 Cookie 即可。

**运行日志在哪？**
`%USERPROFILE%\.longcat_tray\error.log`

**怎么卸载？**
退出托盘程序 + 删除程序文件夹即可。如设置了开机自启，记得从 `shell:startup` 删除快捷方式。
