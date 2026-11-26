{ config, lib, pkgs, utils, ... }:
let
  inherit (lib) mkEnableOption mkOption mkIf types;
  cfg = config.services.epson-printer-utility;
  packages = import ./packages.nix { inherit pkgs; };
  runtime = "/run/epson-printer-utility";
  task = utils.escapeSystemdExecArgs [ "${cfg.package}/bin/epson-printer-cli" "nozzle-check" "--scheduled" "--json" "--device" cfg.device.model ];
in {
  options.services.epson-printer-utility = {
    enable = mkEnableOption "native Epson USB status and maintenance";
    package = mkOption { type = types.package; default = packages.epson-printer-utility; description = "Native GUI and CLI package."; };
    backendPackage = mkOption { type = types.package; default = packages.epson-backend; description = "Native ecbd USB communication daemon."; };
    users = mkOption { type = types.listOf types.str; default = []; description = "Existing users allowed to run maintenance (log in again after changing)."; };
    device = {
      serial = mkOption { type = types.nullOr types.str; default = null; description = "USB serial descriptor, stable across replugging. Required when multiple printers match."; };
      productId = mkOption { type = types.nullOr (types.strMatching "[0-9a-fA-F]{4}"); default = null; description = "Optional four hexadecimal digit USB product ID; vendor is Epson 04b8."; };
      model = mkOption { type = types.str; default = "auto"; description = "CLI selector: auto, USB, or the exact reported model including (USB)."; };
    };
    automaticNozzleCheck = {
      enable = mkEnableOption "periodic native nozzle check (consumes one sheet)";
      onCalendar = mkOption { type = types.str; default = "Sun *-*-* 10:00:00"; description = "systemd OnCalendar expression, in the host timezone unless explicitly specified."; };
    };
  };
  config = mkIf cfg.enable {
    environment.systemPackages = [ cfg.package cfg.backendPackage ];
    users.groups.epson-maintenance = {};
    users.users = { epson-ecbd = { isSystemUser = true; group = "epson-maintenance"; description = "Epson USB backend daemon"; }; }
      // lib.genAttrs cfg.users (_: { extraGroups = [ "epson-maintenance" ]; });
    systemd.tmpfiles.rules = [
      "d ${runtime} 0770 epson-ecbd epson-maintenance -"
      "f ${runtime}/operation.lock 0660 epson-ecbd epson-maintenance -"
    ];
    services.udev.extraRules = let
      selector = ''ATTR{idVendor}=="04b8"''
        + lib.optionalString (cfg.device.productId != null) '', ATTR{idProduct}=="${cfg.device.productId}"''
        + lib.optionalString (cfg.device.serial != null) '', ATTR{serial}=="${cfg.device.serial}"'';
    in ''
      SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ${selector}, GROUP="epson-maintenance", MODE="0660"
    '';
    systemd.services.ecbd = {
      description = "Native Epson USB maintenance communication daemon";
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
    # Available for manual verification even with the timer disabled.
    systemd.services.epson-nozzle-check = {
      description = "One native Epson nozzle check, otherwise log and skip";
      after = [ "ecbd.service" ];
      wants = [ "ecbd.service" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = task;
        User = "epson-ecbd";
        Group = "epson-maintenance";
        TimeoutStartSec = 150;
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
