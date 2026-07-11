# LongCat 用量监控托盘小工具

实时显示 LongCat（`longcat.chat`）Token 用量情况的 Windows 托盘小工具，图标变色 + 右键菜单一目了然。

## ✨ 功能

- 🎨 **图标随余量变色** — 绿色（≥50%）→ 橙色（20~50%）→ 红色（<20%）→ 灰色（获取失败）
- 💬 **悬浮 Tooltip** — 鼠标悬停查看剩余量 / 已消耗 / 预计可用天数
- 📊 **右键菜单直接看详情** — Token 余量、有效期、日均消耗、预计用尽时间、最后刷新时间
- ⏱️ **可自定义刷新间隔** — 手动 / 1 / 5 / 15 / 30 / 60 分钟，自动保存
- 🔔 **用量预警** — 低于阈值弹出系统通知（每次告警周期内只提示一次）
- 🍪 **一键获取 Cookie** — 右键菜单自动打开浏览器，登录后自动抓取保存
- 🚀 **开机自启** — 右键菜单一键设置
- 🛡️ **稳定性保障** — 后台线程异常保护、配置文件容错

## 📥 快速开始

### 下载安装

👉 [📦 下载 LongCatSetup.exe](https://github.com/ChencYet/longcat_tray/releases/latest/download/LongCatSetup.exe)

下载安装程序，双击运行安装向导。安装后从开始菜单或桌面快捷方式启动。

- ✅ 自动创建开始菜单快捷方式
- ✅ 支持开机自启
- ✅ 控制面板一键卸载
- ✅ 可选创建桌面快捷方式

**首次使用：**
1. 从开始菜单启动
2. 右键托盘 → 「自动获取 Cookie」
3. 在弹出的浏览器中登录 longcat.chat
4. 自动抓取 Cookie 并自动刷新获取数据

### 从源码运行

```bash
git clone https://github.com/ChencYet/longcat_tray.git
cd longcat_tray
pip install -r requirements.txt
python main.py
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
立即刷新（自动重载配置）
自动获取 Cookie
编辑 Cookie（记事本）
------------------------------------
刷新间隔 >
  ○ 仅手动刷新
  ● 5 分钟
  ○ 15 分钟
  ○ 30 分钟
  ○ 60 分钟
------------------------------------
✓ 开机自启
------------------------------------
退出
```

| 图标颜色 | 含义 |
|---------|------|
| 🟢 绿色 | 剩余 ≥ 50% |
| 🟠 橙色 | 剩余 20% ~ 50% |
| 🔴 红色 | 剩余 < 20% |
| ⚪ 灰色 | 获取失败（Cookie 可能已失效） |

## 🍪 Cookie 配置

### 方式一：自动获取（推荐）

右键托盘图标 → 「自动获取 Cookie」，在弹出的浏览器窗口中登录 longcat.chat，自动读取浏览器 Cookie 并验证有效性后写入 `config.json`。

### 方式二：手动填写

1. 右键托盘图标 → 「编辑 Cookie（记事本）」打开 `config.json`
2. 浏览器登录 `longcat.chat`
3. 按 `F12` 打开开发者工具 → 选择「网络」→ 筛选「Fetch/XHR」
4. 找到任意 `longcat.chat` 请求 → 「请求标头」→ 复制 `Cookie` 的值
5. 粘贴到 `config.json` 的 `cookie` 字段（引号内），保存
6. 右键托盘图标 → 「立即刷新」（会自动重载配置）

### Cookie 过期更新

右键 → 「自动获取 Cookie」重新抓取即可。

> ⚠️ `config.json` 里的 Cookie 相当于你的登录凭证，**不要**把这个文件夹传到公开仓库。`.gitignore` 已排除 `config.json`。

## 📦 打包

```bash
pip install pyinstaller
pyinstaller LongCatUsage.spec
```

然后使用 Inno Setup 编译安装脚本（需先安装 [Inno Setup](https://jrsoftware.org/isdl.php)）：

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" LongCatSetup.iss
```

打包完成后在 `installer\LongCatSetup.exe` 找到安装程序。

## 🔧 开机自启

右键托盘图标 → 「开机自启」即可开启/关闭。无需管理员权限。

## 🔩 技术栈

- Python 3.10+
- [pystray](https://github.com/moses-palmer/pystray) — 系统托盘
- [Pillow](https://python-pillow.org/) — 图标绘制
- [requests](https://requests.readthedocs.io/) — API 调用
- [playwright](https://playwright.dev/python/) — 浏览器自动化（Cookie 获取）
- [PyInstaller](https://pyinstaller.org/) — 打包为 EXE

## 📁 文件结构

```
longcat_tray/
├── main.py                # 入口，编排各模块
├── config.py              # 配置读写 / 容错
├── api.py                 # 接口请求 / 重试
├── icon.py                # 图标绘制 / 缓存
├── formatter.py           # 数据格式化
├── tray_menu.py           # 菜单构建 / 动作处理
├── state.py               # 共享状态 / 线程锁
├── utils.py               # 弹窗 / 开机自启 / Cookie获取
├── LongCatUsage.spec      # PyInstaller 打包配置
├── LongCatSetup.iss       # Inno Setup 安装脚本
├── config.example.json    # 配置模板
├── requirements.txt       # Python 依赖
├── config.json            # 配置文件（运行时自动生成）
└── .gitignore             # Git 忽略规则
```

## 🙋 FAQ

**Cookie 会过期吗？**
会。LongCat 的登录态一般能维持几天到几周不等。过期后右键 → 「自动获取 Cookie」重新抓取即可。

**运行日志在哪？**
`%USERPROFILE%\.longcat_tray\error.log`

**自动获取 Cookie 需要什么？**
系统已安装 Chrome 或 Edge 浏览器即可，无需额外安装。

**刷新报错怎么办？**
- 手动刷新（点「立即刷新」）：每次出错都会弹通知
- 定时刷新（自动间隔）：只在第一次出错时弹通知，后续静默，图标变灰
- 如果图标变灰，检查 Cookie 是否过期，用「自动获取 Cookie」重新获取即可

**怎么卸载？**
在控制面板"应用和功能"中卸载即可。如设置了开机自启，在右键菜单中关闭即可。
