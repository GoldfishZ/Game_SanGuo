# Windows 可执行文件打包

发行版采用 PyInstaller 文件夹模式。朋友无需安装 Python，解压后双击
`Game_SanGuo.exe` 即可；程序会启动仅限本机访问的服务器并自动打开浏览器。
文件夹模式避免每次启动都解压 PyTorch 和六个模型，也更便于安全软件检查。

## 首次准备

```powershell
python -m pip install -r requirements/build.txt
python -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
```

## 一键构建

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build\build_windows_exe.ps1
```

脚本会自动完成构建、自检和压缩，最终生成：

- `dist\Game_SanGuo\Game_SanGuo.exe`
- `dist\Game_SanGuo_Windows.zip`
- `dist\Game_SanGuo_Windows.sha256`

建议把 ZIP 发给朋友，避免聊天软件直接拦截 EXE。

## 使用说明

1. 完整解压 ZIP，双击根目录中的 `Game_SanGuo.exe`。不要只把 EXE 单独复制出去。
2. 保留弹出的控制台窗口，浏览器会自动进入游戏。
3. 玩完后回到控制台按回车，或直接关闭控制台窗口。

未签名的个人 EXE 可能触发 Windows SmartScreen；朋友需要确认文件确实由你发送，
再选择“更多信息 → 仍要运行”。

当前发行包只包含浏览器实际使用的 WebP 图片，不包含约 140 MB 的开发原图，
因此不会影响游戏显示，但能显著减小分享文件体积。六个 PvE 模型、模型清单、
三档难度逻辑和本地 PvP 均包含在发行包中。构建脚本的自检会真实加载三档选将、
布阵和战斗模型，并验证它们能够完成一次合法推理。
