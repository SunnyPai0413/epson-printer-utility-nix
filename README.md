# Epson Printer Utility — native Nix Flake

独立的 USB 临时维护工具：从本地 Epson Printer Utility 1.1.3 / epson-backend 1.3.1 源码构建原生 Qt 5 GUI、薄 CLI 和 ecbd。按本次最终范围，仅保留工具本身、USB 权限及可选定时任务，不配置打印服务器或打印队列。

## 构建、运行、开发

```sh
# 尚未启用相关 Nix 特性时，给 nix 命令加：
# --extra-experimental-features 'nix-command flakes'
nix build path:.                         # GUI + CLI + ecbd
nix run path:.#gui
nix run path:.#cli -- status --json
nix run path:.#cli -- ink --json
nix run path:.#cli -- nozzle-check
nix run path:.#cli -- clean --confirm-clean  # 一次普通清洗，消耗墨水
nix develop path:.
nix flake check path:.
```

GUI 使用桌面会话的普通用户启动，图片由 Qt 资源系统嵌入，翻译放在 Nix store；设置保存到 `$XDG_CONFIG_HOME/EpsonPrinterUtility`（默认 `~/.config/EpsonPrinterUtility`）。运行前需要 ecbd 和共享运行目录；可选模块如下。本次临时验证使用 [`validation/runtime-test.sh`](validation/runtime-test.sh)，通过本机管理员认证启动临时服务，结束后已停止。

CLI 四个入口均沿用原生 `EPSPrinterController` 与 BackendLib/ecbd。`--device` 支持 `auto`（默认）、`USB` 或完整名称，如 `L805 Series (USB)`。物理 USB 由 ecbd 的序列号/产品 ID 筛选，不依赖 bus/device 编号。后端一次管理一台 USB 设备，匹配多台时拒绝任取第一台。

六色按设备颜色 ID 映射，含 photo/matte black 黑色变体，不猜墨槽次序。`reported_percent` 仅在设备允许显示且值有效时有数值，否则为 `null` / “未知”；`reported_raw` 与 `native_ink_status` 保留原始值和不可用标记。修正了上游 5% 取整、猜测颜色以及丢弃不可用状态的问题。**设备上报值不是墨仓实际液位测量。**

## 可复用的 NixOS 模块

调用方 Flake 增加 `inputs.epson-utility.url = "path:/path/to/epson-printer-utility-nix";`，在 `nixosSystem.modules` 中导入 `inputs.epson-utility.nixosModules.default`，再配置：

```nix
services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ];
  device = {
    serial = "YOUR_USB_SERIAL";   # 多台 Epson 时务必指定，可省略
    productId = "0081";          # 本次 L805 的值，可省略
    model = "L805 Series (USB)";  # 可省略，默认 auto
  };
  automaticNozzleCheck = {
    enable = false;              # 默认关闭
    onCalendar = "Sun *-*-* 10:00:00";
  };
};
```

模块声明独立的 `epson-ecbd` 系统用户、`epson-maintenance` 组、匹配 Epson USB 的 `0660` 规则，以及 `/run/epson-printer-utility` 和维护锁。`users` 指定的用户加入维护组后需要重新登录；设备已接入时重新插拔 USB，使新规则生效。GUI 无需 root；安装模块或临时启动服务需要管理员权限。原生协议仅监听 `127.0.0.1:35587`，不开放防火墙端口；该原生 TCP 接口不带用户认证，本地进程可以连接。

## 定时任务

启用 `automaticNozzleCheck.enable` 才创建 timer。`onCalendar` 使用 systemd 日历表达式，默认按管理机时区，也可显式写时区。任务使用同一个 CLI `nozzle-check --scheduled --json`，只打印一份打印机原生喷嘴检查图案；不判断堵塞，不触发清洗。

```sh
sudo systemctl start epson-nozzle-check.service  # 不启用 timer 也可手动验证一次
journalctl -u epson-nozzle-check.service
```

设备离线、忙碌、缺纸或维护锁被占用时记录原因并跳过，不积压、不补打、不连续重试。timer `Persistent=false`，service `Restart=no`。GUI/CLI 的维护操作共用互斥锁，发送后有限等待状态恢复，不重发。出纸和清洗动作始终需要人工确认。

## 本次实际验证（2026-11-25～26，Asia/Singapore）

| 功能 | 实际结果 |
| --- | --- |
| 状态 | USB L805 实机读取 idle / error=none；清洗后仍为空闲 |
| 六色墨量 | 六色 ID 已读到（黑色为 photo black）；原始值均为 105 / NOREAD，设备关闭墨量信息显示，因此六色均明确显示未知 |
| 喷嘴检查 | 手动启动一次对应 service；用户确认实际图案已出纸并观察到 Y 不清晰。最初纸未推到底，软件记录 unconfirmed，没有自动补打 |
| 普通清洗 | 普通清洗仅调用一次，native_result=0；用户明确确认进行了清洗且已结束 |
| 定期自动喷嘴检查 | 同一个 CLI 的 oneshot service 已实机运行一次；timer 保持关闭；模块检查覆盖默认关闭、不补打、不重启任务 |

原生 GUI 已在真实桌面启动，开发环境已实际进入。检查包括原生状态解析、六色映射/未知值、离线跳过及模块生成的服务/定时器。证据保留在 [`validation/`](validation/)，人工确认记录见 [`physical-confirmation.txt`](validation/physical-confirmation.txt)。

剩余限制：仅 x86_64-linux 已实际构建，aarch64-linux 输出尚未验证；完整模块的专用用户/udev 配置未在管理机激活，本次使用临时 ecbd；GUI 在等待维护状态时可能暂时阻塞；维护后状态读取失败会记录未确认，不会重发。没有再次清洗或清洗后补打，未对黄色图案作自动诊断。临时 ecbd 已停止并释放 USB。没有修改 homelab-infra、部署到 IoT、自动提交或推送。

原始 RPM、未修改 tarball、来源和许可证保留在 [`upstream/SOURCE.md`](upstream/SOURCE.md) 与 [`LICENSES/`](LICENSES/)；适配在 `patches/adapt.py`，不使用 Wine、容器或全局 FHS 环境。ecbd 的公开命令入口仅保留状态/识别/喷嘴检查/普通清洗，不开放 Power Ink Flushing、计数器重置或任意设备指令。
