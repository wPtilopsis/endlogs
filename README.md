# 终末地资源日志助手（endlogs）

本地工具：登录[鹰角客服中心](https://customer-service.hypergryph.com/app/endfield/gamelogs/2)后，按日期查询《明日方舟：终末地》源石 / 嵌晶玉 / 武库配额流水，汇总获取与消耗，并支持生成报告图。

> **非官方工具**。接口可能变更；仅用于查询本人账号数据，请勿分享 token。

---

## 小白用户（推荐）

1. 打开本仓库的 [Releases](../../releases) 页面（若尚未发布，请用下方「从源码一键启动」）。
2. 下载最新 `Endlogs-Windows.zip` 并解压。
3. 双击 **`一键启动.bat`** 或 `Endlogs.exe`。
4. 按页面提示：浏览器登录 → 选日期查询 → 可生成汇总报告。

更细说明见发布包内 `使用说明.txt`，或仓库中的 [`USER_GUIDE.txt`](USER_GUIDE.txt)。

---

## 从源码一键启动（Windows）

需已安装 [Python 3.11+](https://www.python.org/downloads/)（安装时勾选 **Add to PATH**）。

1. 下载或克隆本仓库。
2. 双击项目根目录的 **`一键启动.bat`**。  
   首次运行会自动创建虚拟环境、安装依赖并下载 Chromium，可能较久。
3. 浏览器访问 http://127.0.0.1:8787 （一般会自动打开）。

或手动：

```powershell
cd endlogs
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python launcher.py
```

开发调试也可用：`python main.py`，然后手动打开上述地址。

---

## 功能概览

- 浏览器登录捕获客服 token，并同步 binding 角色信息（渠道 / 昵称 / UID / 区服 / 等级）
- 按日期查询源石、嵌晶玉、武库配额流水（支持分页 `seqId`）
- 汇总：期初、期末、净变化、获取 / 消耗
- 按原因分类统计（映射见 `config.py`）
- 明细默认折叠；可导出 CSV
- 汇总报告：预览后确认保存为 PNG

---

## 打包 Windows 发布包（维护者）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

产物在 `dist\Endlogs\`。可将该文件夹压成 zip，上传到 GitHub Release。

说明：完整包若附带 Playwright 浏览器，体积会到数百 MB；也可不附带浏览器，让用户本机已装过 Chromium。

---

## 目录结构

```text
endlogs/
  launcher.py          # 一键启动（起服务 + 开浏览器）
  一键启动.bat
  main.py              # 仅启动 API
  app/ auth/ client/ stats/ web/
  config.py
  endlogs.spec         # PyInstaller
  scripts/build_windows.ps1
  USER_GUIDE.txt
```

---

## 已知枚举

| 字段 | 值 | 含义 |
|------|-----|------|
| currencyType | 1 | 源石 |
| currencyType | 2 | 嵌晶玉 |
| currencyType | 3 | 武库配额 |
| changeType | 0 / 1 / 2 | 全部 / 获取 / 消耗 |

Token 保存在本地 `data/`（已 gitignore），请勿提交到 Git。

---

## License

MIT。与鹰角网络 / Hypergryph 无关。
