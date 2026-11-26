# SPDX-License-Identifier: GPL-2.0-or-later
{ config, lib, pkgs, utils, ... }:
let
  inherit (lib) mkEnableOption mkOption mkIf types;
  cfg = config.services.epson-printer-utility;
  packages = import ./packages.nix { inherit pkgs; };
  runtime = "/run/epson-printer-utility";
  task = utils.escapeSystemdExecArgs [ "${cfg.package}/bin/epson-printer-cli" "nozzle-check" "--scheduled" "--json" "--device" cfg.device.selector ];
  connection = if cfg.usb.enable then "all" else "network";
in {
  options.services.epson-printer-utility = {
    enable = mkEnableOption "native Epson USB/network status and maintenance";
    package = mkOption { type = types.package; default = packages.epson-printer-utility; description = "Native GUI and CLI package."; };
    backendPackage = mkOption { type = types.package; default = packages.epson-backend; description = "Native ecbd USB daemon and ecblp CUPS backend."; };
    usb.enable = mkOption { type = types.bool; default = true; description = "Enable USB permissions and ecbd. Set false for a network-only installation."; };
    cups.enable = mkEnableOption "optional ecblp integration via services.printing.drivers (requires USB); never creates queues";
    users = mkOption { type = types.listOf types.str; default = []; description = "Existing users allowed to run maintenance; log in again after changing."; };
    device = {
      serial = mkOption { type = types.nullOr types.str; default = null; description = "USB serial descriptor, stable across replugging. Required when multiple printers match."; };
      productId = mkOption { type = types.nullOr (types.strMatching "[0-9a-fA-F]{4}"); default = null; description = "Optional four hexadecimal digit USB product ID; vendor is Epson 04b8."; };
      model = mkOption { type = types.str; default = "auto"; description = "Legacy name for the scheduled CLI selector; prefer device.selector."; };
      selector = mkOption { type = types.str; default = cfg.device.model; description = "Scheduled device selector: native ID/address from devices, USB, exact model, or auto (requires a unique match)."; };
    };
    automaticNozzleCheck = {
      enable = mkEnableOption "periodic native nozzle check (consumes one sheet)";
      onCalendar = mkOption { type = types.str; default = "Sun *-*-* 10:00:00"; description = "systemd OnCalendar expression, in the host timezone unless explicitly specified."; };
    };
  };
  config = mkIf cfg.enable {
    assertions = [{ assertion = !cfg.cups.enable || cfg.usb.enable; message = "epson-printer-utility.cups requires usb.enable; network printers use their native CUPS transport."; }];
    environment.systemPackages = [ cfg.package ] ++ lib.optional cfg.usb.enable cfg.backendPackage;
    environment.sessionVariables.EPSON_CONNECTION = connection;
    users.groups.epson-maintenance = {};
    users.users = { epson-ecbd = { isSystemUser = true; group = "epson-maintenance"; description = "Epson utility service account"; }; }
      // lib.genAttrs cfg.users (_: { extraGroups = [ "epson-maintenance" ]; })
      // lib.optionalAttrs cfg.cups.enable { cups.extraGroups = [ "epson-maintenance" ]; };
    systemd.tmpfiles.rules = [
      "d ${runtime} 0770 epson-ecbd epson-maintenance -"
      "f ${runtime}/operation.lock 0660 epson-ecbd epson-maintenance -"
      "f ${runtime}/fifo.lock 0660 epson-ecbd epson-maintenance -"
    ] ++ lib.optional cfg.usb.enable "p ${runtime}/ecblp0 0660 epson-ecbd epson-maintenance -"
      ++ lib.optionals cfg.cups.enable [
        # CUPS backends retain lp, but may drop supplementary groups.
        # Default ACLs also cover files recreated by ecbd.
        "a+ ${runtime} - - - - g:lp:rwx,d:g:lp:rwx"
        "a+ ${runtime}/ecblp0 - - - - g:lp:rw"
        "a+ ${runtime}/fifo.lock - - - - g:lp:rw"
        "a+ ${runtime}/operation.lock - - - - g:lp:rw"
      ];
    services.udev.extraRules = mkIf cfg.usb.enable (let
      selector = ''ATTR{idVendor}=="04b8"''
        + lib.optionalString (cfg.device.productId != null) '', ATTR{idProduct}=="${lib.toLower cfg.device.productId}"''
        + lib.optionalString (cfg.device.serial != null) '', ATTR{serial}=="${cfg.device.serial}"'';
    in ''
      SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ${selector}, GROUP="epson-maintenance", MODE="0660"
    '');
    systemd.services.ecbd = mkIf cfg.usb.enable {
      description = "Native Epson USB printing and utility daemon";
      wantedBy = [ "multi-user.target" ];
      after = [ "systemd-udev-trigger.service" "systemd-tmpfiles-setup.service" ];
      environment = lib.optionalAttrs (cfg.device.serial != null) { EPSON_USB_SERIAL = cfg.device.serial; }
        // lib.optionalAttrs (cfg.device.productId != null) { EPSON_USB_PRODUCT = cfg.device.productId; };
      serviceConfig = {
        Type = "simple";
        ExecStart = "${cfg.backendPackage}/bin/ecbd";
        User = "epson-ecbd";
        Group = "epson-maintenance";
        UMask = "0007";
        Restart = "on-failure";
        RestartSec = 5;
        TimeoutStopSec = 10;
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        ReadWritePaths = [ runtime ];
        NoNewPrivileges = true;
        RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_NETLINK" ];
      };
    };
    services.printing.enable = mkIf cfg.cups.enable (lib.mkDefault true);
    services.printing.drivers = lib.optional cfg.cups.enable cfg.backendPackage;
    systemd.services.cups = mkIf cfg.cups.enable {
      after = [ "ecbd.service" "systemd-tmpfiles-setup.service" ];
      wants = [ "ecbd.service" ];
    };
    systemd.services.epson-nozzle-check = {
      description = "One native Epson nozzle check, otherwise log and skip";
      after = [ "systemd-tmpfiles-setup.service" ] ++ lib.optional cfg.usb.enable "ecbd.service";
      wants = lib.optional cfg.usb.enable "ecbd.service";
      environment.EPSON_CONNECTION = connection;
      serviceConfig = {
        Type = "oneshot";
        ExecStart = task;
        User = "epson-ecbd";
        Group = "epson-maintenance";
        TimeoutStartSec = 180;
        Restart = "no";
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        ReadWritePaths = [ runtime ];
      };
    };
    systemd.timers.epson-nozzle-check = mkIf cfg.automaticNozzleCheck.enable {
      description = "Optional Epson nozzle check schedule";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.automaticNozzleCheck.onCalendar;
        Persistent = false;
        RandomizedDelaySec = 0;
        AccuracySec = "1min";
        Unit = "epson-nozzle-check.service";
      };
    };
  };
}
