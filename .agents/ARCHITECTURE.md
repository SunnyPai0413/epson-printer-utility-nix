# 架构上下文

[Agent 索引](../AGENTS.md) · [设计决策](DECISIONS.md)

## 组件与源码入口

| 组件 | 作用 | 入口 |
| --- | --- | --- |
| Qt GUI | 设备选择、状态、墨量、维护交互 | 保留的 Utility `PrinterUtility/`，适配见 [adapt.py](../patches/adapt.py) |
| CLI | 六个命令、设备筛选、结果与退出码 | [cli.cpp](../src/cli.cpp) |
| 公共报告模型 | 状态／错误／警告、墨色、原生进纸计数 | [native-report.h](../src/native-report.h)、[native-count.h](../src/native-count.h) |
| EPSCommonLib | 原生设备发现、网络通信和维护 API | Utility 归档中的 `EPSCommonLib/` |
| ecbd | 独占所选 USB 设备，提供本机状态与打印数据通道 | Backend 归档中的 `daemon/` |
| ecblp | CUPS 后端，将打印机字节流写入 ecbd FIFO | Backend `src/backend.c`，适配见 [adapt.py](../patches/adapt.py) |
| NixOS 模块 | 服务账户、USB 权限、运行目录、ACL、可选 CUPS 和 timer | [module.nix](../nix/module.nix) |

原始组件来自 [上游归档](UPSTREAM.md)，在构建沙箱解包；仓库中的已忽略解包目录不是打包输入。

## 三条运行路径

- USB 状态／维护：GUI 或 CLI → EPSCommonLib 的 USB 适配 → 本机 ecbd → USB 打印机。
- Epson 原生网络：GUI 或 CLI → EPSCommonLib 网络发现／连接 → 网络打印机。网络模式不依赖 ecbd，尚无网络设备实机验证。
- CUPS USB 打印：客户端 → CUPS → 机型过滤器（普通队列）或 RAW 透传 → ecblp → FIFO → ecbd → USB。

普通队列在 Linux 上用 `pkgs.epson-escpr` 等机型驱动渲染。Windows RAW 队列由 Windows Epson 原厂驱动渲染；本项目不实现该驱动的质量档、实际喷墨模式或 Power Ink Flushing。两类队列的用户配置见 [打印指南](../docs/PRINTING.md)。

远程 IPP 是 CUPS 的服务接口，不是 Epson 原生网络维护。网络打印机直接接收其他主机的作业时，也不受本机共享锁控制。

## USB 设备与标识

ecbd 一次管理一台 USB 打印机。多台匹配时拒绝任取设备，由 `device.serial`／`productId` 筛选；更换 daemon 管理的设备需要调整配置并重启服务。

CLI 的 `--device` 接受原生 ID、已发现地址、完整型号或 `auto`；匹配不唯一时拒绝执行。原生 1284 序列号与模块筛选的 USB descriptor 序列号可能不同，字段语义见 [JSON 接口](../docs/JSON.md)。

## 共享资源与锁

运行目录固定为 `/run/epson-printer-utility`：

| 资源 | 使用者与用途 |
| --- | --- |
| `ecblp0` | ecblp 写入、ecbd 读取的 FIFO |
| `operation.lock` | 打印提交与 GUI／CLI／oneshot 维护共用的排他操作锁 |
| `fifo.lock` | FIFO 写入串行化，避免多个写入者交错 |

具体实现见 [operation-lock.h](../src/operation-lock.h)、[backend-io.h](../src/backend-io.h) 和 `adapt.py`。
GUI／CLI 维护以非阻塞方式取操作锁，再检查设备空闲，发送一次原生命令并等待后续状态；ecblp 等待操作锁和写入锁后转发数据。

Windows 驱动不直接获取 Linux 锁，经 RAW 队列进入 ecblp 的数据才使用这些锁。FIFO 写入完成不能证明设备已完成长时间维护；维护与打印重叠的完整实机行为仍未验证。

## 服务与权限

`epson-ecbd` 服务账户和 `epson-maintenance` 组由模块创建。配置的已有用户加入该组，重新登录后生效。
ecbd 仅监听 `127.0.0.1:35587`；上游本机 TCP 接口无用户认证，模块不向网络开放它。

启用 CUPS 集成时，模块安装后端并为 CUPS 的 `lp` 组设置运行目录／FIFO／锁 ACL。
默认 ACL 覆盖 ecbd 重建的文件，tmpfiles 在重启后恢复访问权限。模块不创建或迁移队列。
CUPS 的局域网监听、允许范围和 631 端口由用户显式配置。

## 报告与界面

GUI 和 CLI 共用状态报告。设备故障与通信失败分开，警告不覆盖错误；墨色列表、原始 ID 和未知值由原生报告决定。
GUI 维护等待在 worker 中执行，期间禁用重复提交；关闭维护窗口会等待工作结束。
JSON schema 及计数语义以 [用户接口文档](../docs/JSON.md) 为准。
