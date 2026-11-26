# Epson USB 打印与 Windows 原厂驱动接入

[返回首页](../README.md) · [安装配置](INSTALL.md) · [JSON 接口](JSON.md)

本文使用已启用的 ecbd 和 ecblp USB 后端。普通队列负责 Linux 端渲染，RAW 队列接收 Windows 原厂驱动已生成的数据；两者可指向同一台 L805。

## 普通 ESC/P-R 队列

在[安装指南](INSTALL.md#nixos推荐模块安装)的 USB 模块配置基础上启用 CUPS，并在接受 `pkgs` 参数的系统模块（如 `configuration.nix`）中加入机型驱动。L805 示例：

```nix
services.epson-printer-utility.cups.enable = true;
services.printing.drivers = [ pkgs.epson-escpr ];
```

模块会启用 CUPS（若未配置），自动把 ecblp 所在的 `backendPackage` 加入 `services.printing.drivers`，并通过用户组和 tmpfiles ACL 授予 CUPS 后端使用的 `lp` 组 FIFO／锁访问权限；目录的默认 ACL 覆盖服务重建文件的情况，重启后会重新应用。仅将 `#epson-backend` 放入驱动列表不足以完成这些服务与权限配置。

ecblp 是 USB **传输后端**，不包含机型 PPD 或渲染过滤器；`pkgs.epson-escpr` 在此提供 L805 的渲染驱动。其他机型需自行核实驱动与上游支持，尚未实机验证。应用 NixOS 配置后，先查询后端与实际可用的 L805 型号标识：

```sh
lpinfo -v
lpinfo -m | grep -i L805
```

ecbd 就绪后应能发现 URI：

```text
ecblp:/run/epson-printer-utility/ecblp0
```

将 `lpinfo -m` 输出中匹配 L805 的**第一列**替换下例的 `MODEL_FROM_LPINFO`，手动创建名为 `Epson_L805` 的队列（也可在 `http://localhost:631` 中选择同一 URI 和机型驱动）：

```sh
sudo lpadmin -p Epson_L805 -E \
  -v 'ecblp:/run/epson-printer-utility/ecblp0' \
  -m 'MODEL_FROM_LPINFO'
lpstat -v Epson_L805
```

装纸后可主动提交一份自己的 PDF，并检查任务：

```sh
lp -d Epson_L805 /path/to/test.pdf
lpstat -W not-completed -o Epson_L805
```

任务完成状态仍需结合实际出纸确认。模块不会创建、迁移或修改任何打印队列。已有队列可由用户在 CUPS 中修改 URI 和驱动；ecbd 管理的 USB 设备应通过 ecblp 打印，其他直接抢占同一 USB 接口的队列无法与它共享连接。直接连接网络打印机的队列继续使用自身的网络传输，无需 ecblp。

ecblp 和维护工具共用 `/run/epson-printer-utility` 下的 FIFO、写入锁和操作锁，避免 USB 打印数据与维护命令交错；维护前重新检查设备是否空闲。发往本机 CUPS 的远程 IPP 作业也经 ecblp 使用这些锁；其他主机直接向网络打印机发送的作业不受本机维护锁控制。ecbd 仅监听 `127.0.0.1:35587`，不开放防火墙；上游本地 TCP 接口无用户认证。正常打印所需的取消、复位和特定继续打印通路仅保留在后端内部，CLI 没有对应维护入口。

v1.0.0 包含 ecblp 的 FIFO 背压修复：读端存活但消费较慢时继续等待，同时保留 CUPS 取消能力；读端消失或 I/O 失败时明确失败，不自动重放打印数据。2026-11-26 已验证 L805 远程 IPP 多页 PDF 输出，重启后 ACL、CUPS 服务及打印任务验证通过。

## 局域网 IPP 共享

路径为 **客户端 → IPP → NixOS CUPS → 机型驱动 → ecblp/ecbd → USB L805**。Epson 原生网络发现／维护是另一条通路，尚未实机验证。

默认模块只提供本机接入。若需要共享，按实际受信局域网设置 CUPS 监听与允许范围；替换下面的主机地址和网段，然后应用配置：

```nix
services.printing = {
  listenAddresses = [ "localhost:631" "192.168.1.10:631" ];
  allowFrom = [ "localhost" "192.168.1.0/24" ];
  openFirewall = true;
};
```

在打印主机上共享刚创建的队列：

```sh
sudo lpadmin -p Epson_L805 -o printer-is-shared=true
```

客户端可添加 `ipp://PRINT_SERVER_IP:631/printers/Epson_L805`。有 CUPS 客户端命令时，可直接向打印主机提交多页 PDF；将 `PRINT_SERVER_IP` 替换为实际地址：

```sh
lp -h PRINT_SERVER_IP:631 -d Epson_L805 /path/to/multipage.pdf
lpstat -h PRINT_SERVER_IP:631 -W not-completed -o Epson_L805
```

这里共享的是 CUPS 的 631 端口；ecbd 的 35587 端口保持本机监听。若任务失败，先检查 `journalctl -u cups.service -u ecbd.service`；权限问题可用 `getfacl /run/epson-printer-utility{,/ecblp0,/fifo.lock,/operation.lock}` 核对 `lp` 组 ACL，再检查队列 URI、驱动及实际出纸情况。

## Windows 原厂驱动：CUPS IPP RAW 队列

Windows 可用对应机型的 Epson 原厂驱动生成打印机数据，经 CUPS RAW 队列原样转发到 ecblp/ecbd。路径为 **Windows 应用 → Epson Windows 原厂驱动 → IPP → CUPS RAW 队列 → ecblp/ecbd → USB L805**。介质和质量选项由 Windows 驱动提供，服务器不再使用 Linux ESC/P-R 过滤器重新渲染。这里的 RAW 指队列透传，网络传输仍使用 IPP 的 631 端口。

先完成上文 USB／CUPS 服务、权限和局域网 IPP 共享配置。RAW 队列本身不需要机型 PPD；已有的 `pkgs.epson-escpr` 可继续供普通队列使用。使用单独的队列名创建 RAW 队列，保留原来的 `Epson_L805`：

```sh
sudo lpadmin -p Epson_L805_RAW -E \
  -v 'ecblp:/run/epson-printer-utility/ecblp0' \
  -m raw \
  -o printer-is-shared=true
lpstat -v Epson_L805_RAW
lpstat -p Epson_L805_RAW
```

`-m raw` 会移除指定队列的 PPD，因此不要将上面的队列名改成已有的普通队列名。模块不会自动创建这个队列；也不需要第二个 ecbd、额外 USB 后端或新的锁配置。

在 Windows 上接入：

1. 从 Epson 官方支持页安装与 Windows 版本、架构及 L805 对应的原厂驱动。若系统缺少传统 IPP 客户端，在“启用或关闭 Windows 功能 → 打印和文档服务”中启用“Internet 打印客户端”，按系统提示完成安装。
2. 打开添加打印机的手动添加向导，选择“按名称选择共享打印机”，输入 `http://PRINT_SERVER_IP:631/printers/Epson_L805_RAW`，将主机地址替换为上文配置的打印服务器地址。
3. 选择 **Epson L805 原厂驱动**；必要时用“从磁盘安装”选择其 INF。安装完成后，在“打印机属性 → 高级”核对驱动名称，在“端口”页确认上述 IPP 地址。若自动绑定了 Microsoft IPP Class Driver，改用已安装的 Epson 原厂驱动并保留这个端口。
4. 在该 Windows 打印机的“打印首选项”中选择 A4、与实际相纸匹配的介质及高质量，再由 Windows 应用提交照片。喷嘴检查和大墨量冲洗使用原厂驱动的维护页；本项目的 `clean` 仍仅执行普通清洗。

此方案要求 Windows 允许安装和使用第三方打印驱动；启用了 Windows 受保护打印模式的环境不能使用该原厂驱动路径，参见 [Microsoft 说明](https://learn.microsoft.com/en-us/windows/modern-print/windows-protected-print-mode/windows-protected-print-mode)。Windows 双向状态／墨量查询是否可用仍未验证。

两个队列可同时保留，按客户端是否已经渲染数据选择目的队列：

| 队列 | 提交内容 | 服务器处理 |
| --- | --- | --- |
| `Epson_L805` | Linux／普通 IPP 客户端的 PDF 等文档 | 使用 L805 PPD 和 ESC/P-R 过滤器渲染 |
| `Epson_L805_RAW` | Windows Epson 原厂驱动生成的打印机数据 | 透传至同一个 ecblp URI |

普通 PDF／图片直接提交给 RAW 队列不会获得服务器端渲染；Windows 原厂驱动的数据应提交到 RAW 队列，避免交给普通队列再次处理。两个队列复用 `/run/epson-printer-utility/operation.lock` 和 `fifo.lock`，由 ecblp 串行化作业写入；本项目 GUI／CLI／oneshot 维护继续使用现有操作锁和空闲检查。Windows 驱动本身不直接获取 Linux 锁，只有经 ecblp 提交的数据经过这些锁。后端传输结束也不代表大墨量冲洗等设备动作已经完成；待实际动作完成后再从任一队列打印或发起维护，打印期间主动触发维护的行为尚未验证。

## CUPS RAW 弃用限制

本方法适用于仍支持 `-m raw` 和传统后端的 CUPS 2.x 环境。创建时可能出现 RAW／驱动弃用警告；若该版本已拒绝创建 RAW 队列，此方法不可用。上游已弃用 RAW、PPD 驱动和传统后端；CUPS 3 使用 IPP／Printer Application 架构，本文的队列与 ecblp 接入方式不能直接照搬，本项目尚未提供对应迁移实现。参见 [lpadmin 手册](https://openprinting.github.io/cups/doc/man-lpadmin.html) 和 [CUPS v3 架构](https://openprinting.github.io/cups/cups3.html)。

2026-11-26 维护者确认 L805 在该 Windows 原厂驱动／IPP RAW／USB 路径上完成了高质量 A4 相纸打印、喷嘴检查和大墨量冲洗。**实际喷墨 DPI、光盘打印及 Windows 双向状态查询尚未验证**；驱动中的“高质量”选项不构成实际 DPI 的测量。确认来自维护者的实机反馈，未附新的原始硬件日志；其他兼容性范围见[首页](../README.md#兼容性与验证范围)。
