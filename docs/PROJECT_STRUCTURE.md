# 项目结构说明

工程采用“根目录兼容入口 + `src` 源码包 + 分类工具”的组织方式。

## 入口层

- `main.py`：兼容 CLI/Pygame 启动命令，实际实现位于 `src/app/cli.py`。
- `main_web.py`：兼容 Web 启动和测试导入，实际实现位于 `src/web/server.py`。
- `desktop_launcher.py`：PyInstaller 入口，实际实现位于 `src/web/desktop.py`。

根目录文件只负责转发，业务逻辑不应继续写入这些兼容入口。

## 源码层

- `src/app/`：应用编排和 CLI 菜单。
- `src/battle/`：战斗回合编排和战斗上下文。
- `src/game_data/`：武将、技能、被动、生平与查询接口。
- `src/models/`：武将、队伍、游戏流程等领域模型。
- `src/skills/`：技能抽象基类。
- `src/ui/`：CLI 回调和旧 Pygame 界面。
- `src/web/`：HTTP 服务、桌面启动器和浏览器静态资源。
- `src/paths.py`：源码运行和 PyInstaller 环境共用的资源路径。

## 工具层

- `tools/testing/`：单元测试运行器、自走模拟、浏览器压力测试和 HTML 检查。
- `tools/build/`：Windows 发行包构建。
- `tools/assets/`：图片转换和资源优化。
- `tools/maintenance/`：已经应用过但仍保留备查的一次性维护脚本。

## 依赖与产物

- `requirements.txt`：CLI/Pygame 和测试环境依赖。
- `requirements/build.txt`：发行包构建依赖。
- `assets/`：源图片及 WebP 运行图片。
- `artifacts/`：测试报告和截图，不进入版本控制。
- `build/`、`dist/`：PyInstaller 中间目录和发行文件，不进入版本控制。

新增代码时应优先放入对应 `src` 子包；新增脚本应按用途放入对应 `tools` 子目录，
避免再次向根目录添加一次性脚本。
