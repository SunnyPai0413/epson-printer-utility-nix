# 上游与适配上下文

[Agent 索引](../AGENTS.md) · [架构](ARCHITECTURE.md)

## 保留的输入与许可

输入是本地提供的 Epson `epson-printer-utility-1.1.3-1.src.rpm`，包含 Printer Utility 1.1.3 和 epson-backend 1.3.1。
原始下载地址与日期没有提供，不补猜。归档、提取说明和 SHA-256 的唯一来源为 [upstream/SOURCE.md](../upstream/SOURCE.md) 与 [SHA256SUMS](../upstream/SHA256SUMS)。

[Nix 包定义](../nix/packages.nix) 在沙箱中解包两份保留的 tarball，然后执行 [patches/adapt.py](../patches/adapt.py)。
构建不下载其他 Epson 上游版本，不使用预编译 Epson 库、Wine 或 FHS 容器。
`upstream/epson-printer-utility/`、`upstream/epson-backend/`、`.work/` 和 `result*` 是已忽略的本地材料，不能替代归档输入。

新增代码采用 GPL-2.0-or-later；上游 Utility、Backend 以及其 ESC/P-R、epsmp、JPEG、libltdl 等组件保留各自许可证和例外。
完整声明见 [NOTICE.md](../NOTICE.md)、[LICENSE](../LICENSE) 和 [LICENSES/](../LICENSES/)。
COPYING、AUTHORS、README 与文件级声明保留在原始归档中；libltdl 源码保留但不被现有 CMake 构建链接。

## 适配位置

| 适配区域 | 现有改动 |
| --- | --- |
| `BackendLib/backend_api.c/.h` | 原生 USB 状态、ST2 墨色／墨量及进纸计数，保留设备标识和未知值 |
| `EPSCommonLib` USB／网络适配 | USB 使用 ecbd；恢复 EPSCommonLib 原生网络发现和连接，不将网络路径转入 daemon |
| `EPSPrinterController`／CLI | 唯一设备筛选、共用报告、维护操作锁、空闲复查、单次提交及结果区分 |
| `PrinterUtility/` | 墨色列表、设备选择、Qt 资源路径、维护 worker 和禁用重复提交 |
| Backend `src/backend.c` | 原生 ecblp、FIFO 传输、等待背压、取消、I/O 诊断和失败不重放 |
| Backend `daemon/` | USB 选择、共享 FIFO 路径及并发写入控制 |

新增的公共实现位于 [src/](../src/)；Nix/CMake 构建入口见 [开发构建上下文](DEVELOPMENT.md)。
详细的文件级改动以 `adapt.py` 和生成的 `UPSTREAM-MODIFICATIONS.txt` 为准，表格仅用于定位。

## 修改声明与随包材料

适配脚本为每个被修改的上游 C/C++ 文件添加显著的项目修改声明，日期固定为 `2026-11-26`，原始声明保留在其后。
固定日期描述当前适配修订，不读取构建机时钟，以保持构建可复现。
生成的 `UPSTREAM-MODIFICATIONS.txt` 随包安装；现有 `upstream-modification-notices` 检查将适配树与保留归档比较。

包还安装上游 COPYING／AUTHORS／README、项目 LICENSE／NOTICE／CHANGELOG 和第三方许可副本。
这些安装行为由现有 [CMakeLists.txt](../CMakeLists.txt) 定义；文档迁移不改变安装清单。

## 分辨率与功能边界

本项目的 ecblp/ecbd 负责传输，Utility 提供状态和有限维护接口，不包含 Linux 机型 PPD／打印渲染器。
普通 L805 队列由独立的 `pkgs.epson-escpr` 提供渲染；Windows RAW 队列由 Windows 原厂驱动提供渲染和维护选项。
高质量 A4 相纸输出已有人确认，但实际喷墨 DPI、光盘打印和 Windows 双向状态查询没有验证，不能从选项名称推导。
