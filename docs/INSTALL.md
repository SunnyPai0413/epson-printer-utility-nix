# 安装与维护工具配置

[返回首页](../README.md) · [打印配置](PRINTING.md) · [JSON 接口](JSON.md)

## Nix 与包安装

包输出面向 `x86_64-linux`、`aarch64-linux`。需要安装 Nix 并启用 `nix-command`、`flakes` 特性；NixOS 可在系统配置中设置：

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

尚未启用这些特性时，也可将下文命令开头的 `nix` 替换为 `nix --extra-experimental-features 'nix-command flakes'`，临时启用后构建或运行。

应用配置后，推荐固定 **Git Tag**，并保留调用方的 `flake.lock`。以下公开引用在维护者发布 `v1.0.0` Tag 后可用：

```sh
nix build github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#default
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#cli -- --help
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#gui
```

`nix build` 的结果位于 `./result`；`nix run` 临时运行应用。默认包包含 GUI、CLI、ecbd 和 `lib/cups/backend/ecblp`。也可分别构建 `#epson-printer-utility`（GUI／CLI）和 `#epson-backend` / `#ecblp`（同一个后端包）。构建或运行包本身不会安装系统服务、USB 权限或 CUPS 队列。

### NixOS：推荐模块安装

模块负责运行目录、维护锁、访问组和 USB 服务。将下面结构合并进现有 `flake.nix`；保留已有的 `nixpkgs` input 和系统模块，把 `your-host`、架构替换为自己的配置：

```nix
{
  inputs.epson-utility.url = "github:SunnyPai0413/epson-printer-utility-nix/v1.0.0";

  outputs = inputs@{ nixpkgs, ... }: {
    nixosConfigurations.your-host = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux"; # 或 aarch64-linux
      modules = [
        ./configuration.nix
        inputs.epson-utility.nixosModules.default
      ];
    };
  };
}
```

在 `configuration.nix` 中加入 USB 配置；`your-user` 必须是已存在的普通用户：

```nix
services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ]; # 已存在的桌面用户
  usb.enable = true;      # 默认值
  # 多台 Epson USB 设备时，指定设备实际的 serial / productId：
  # device.serial = "YOUR_USB_SERIAL";
  # device.productId = "YOUR_4_HEX_DIGIT_ID";
};
```

从你的系统配置目录应用配置，再重新登录使组权限生效；已连接的 USB 设备可能需要重新插拔：

```sh
sudo nixos-rebuild switch --flake .#your-host
systemctl status ecbd.service
epson-printer-cli devices --connection usb --json
```

模块会安装 `epson-printer-utility` 和 `epson-printer-cli`。GUI 由桌面普通用户启动。ecbd 一次管理一台 USB 打印机；多台匹配时拒绝任取第一台，用模块的 USB 描述符序列号筛选。更换被 daemon 管理的 USB 设备需要调整筛选并重启服务，不支持在 GUI 中动态接管多台 USB 设备。CUPS 打印还需完成[打印配置](PRINTING.md)。

### NixOS：仅网络维护（尚未实机验证）

在已导入模块的系统配置中，使用：

```nix
services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ];
  usb.enable = false;
};
```

这不会启用 ecbd、USB 规则或安装 USB 后端。网络发现、连接和维护直接走上游 EPSCommonLib，不需要 USB 设备，不通过 ecbd 转发，也不需要暴露其端口。发现范围和可用功能取决于上游协议、网络可达性和设备。原生网络发现通常需要等待数秒；跨网段发现未验证。

只运行网络发现／状态查询可直接使用固定 Tag 的 `#cli`，无需模块。执行维护还需要模块创建的共享锁和相应访问权限。**CUPS 远程 IPP 打印验证不代表 Epson 原生网络维护已经验证。**

### 其他 Linux 发行版

其他 Linux 发行版可以安装 Nix，使用上述 Flake 包构建及运行 GUI／CLI；这不等同于完整的系统集成。当前没有 `.deb`、`.rpm`、原生安装器，也没有面向其他发行版的服务安装集成。USB daemon、udev 权限、运行目录／锁、CUPS ACL 和驱动接入需要自行配置；本文的模块安装与实机验证面向 NixOS。

## 使用 Cachix 缓存

将下例 `YOUR-CACHE-NAME` 替换为维护者配置的 `CACHIX_CACHE_NAME` 实际值；本地不会自动读取 GitHub Actions Variable：

```sh
CACHIX_CACHE_NAME='YOUR-CACHE-NAME'
nix run nixpkgs#cachix -- use "$CACHIX_CACHE_NAME"
nix build github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#default
```

按 `cachix use` 输出的提示完成 Nix 配置。NixOS 用户将实际缓存地址与公钥加入 `nix.settings.extra-substituters`、`nix.settings.extra-trusted-public-keys` 后应用系统配置；公钥可从该缓存的 Cachix 页面获取。公共缓存下载无需写入 Token。若选择私有缓存，下载者还需配置自己的只读凭据，见 [Cachix 使用说明](https://docs.cachix.org/using-a-cache)。

缓存按实际 store 路径匹配。建议固定 `v1.0.0` Tag，并确认该 Tag 对应的 CI 已成功，保持锁文件与架构一致；`#epson-printer-utility`、`#epson-backend`、`#ecblp` 以及 NixOS 模块安装也使用同一套 Nix 缓存机制。项目版本号变化会产生新的 store 路径，发布前基线的缓存不保证命中 v1.0.0 产物。

## 设备选择与结果含义

`--device` 支持原生 ID（如 `USB:序列号` 或发现得到的网络 ID）、已发现的网络地址、完整型号名和 `auto`。`auto` 或型号匹配多台时拒绝执行。没有序列号的 USB ID 为 `USB`。`--connection all|usb|network` 限定发现范围；`USB` / `USB:…` 选择器默认只查 USB。纯网络模块将 GUI／CLI 默认范围设为 `network`，仍可显式覆盖 CLI 范围。

GUI 保留原生打印机选择和维护界面，列表显示设备 ID。维护在后台执行，期间禁用重复提交；一次命令发送后最多约两分钟等待状态，失败或超时显示“未确认”，不会自动重发。关闭正在维护的窗口会等待当前工作结束，避免销毁通信库。

墨色根据设备列表逐项显示，不固定为六色，不把 photo black、matte black 等不同颜色合并。设备不允许显示、状态不可读或值无效时为“未知”／JSON `null`；不猜颜色或按档位伪造百分比。**设备上报百分比不是墨仓实际液位测量。** 没有颜色列表时显示未知，JSON 为 `[]`。

`paper-count` 沿用原生计数接口，逐项保留未知值；总数只在彩色和黑白计数都有效时相加。它表示设备进纸计数，**不是成功打印页数**，也不是可重置的废墨计数器。设备不支持或未上报时明确不可用。

v1.0.0 使用 **JSON schema 2**，与本地早期版本相比含兼容性变化；`project_version` 为 `1.0.0`，两个上游版本仍分别为 `1.1.3` / `1.3.1`。脚本接入或升级前请阅读 [JSON 字段与退出码](JSON.md)。

## 可选定时喷嘴检查

默认关闭。只在明确需要自动消耗纸张打印原生图案时开启，并设置唯一设备：

```nix
services.epson-printer-utility = {
  device.selector = "NATIVE_ID_FROM_DEVICES";
  automaticNozzleCheck = {
    enable = true;
    onCalendar = "Sun *-*-* 10:00:00";
  };
};
```

日历按主机时区解释，也可在表达式中指定时区。离线、忙碌、设备错误或锁被占用时记录原因并跳过；`Persistent=false`、`Restart=no`，不积压补打，不自动清洗。任务日志：

```sh
journalctl -u epson-nozzle-check.service
```

未开启 timer 时也有对应 oneshot service；手动启动它会实际打印一份图案。

许可证与第三方声明见 [NOTICE.md](../NOTICE.md)，保留的原始源码及校验值见 [upstream/SOURCE.md](../upstream/SOURCE.md)。
