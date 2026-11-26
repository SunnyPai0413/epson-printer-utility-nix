# SPDX-License-Identifier: GPL-2.0-or-later
{ nixpkgs, system, module }:
let
  pkgs = nixpkgs.legacyPackages.${system};
  eval = extra: (nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ module { system.stateVersion = "26.05"; services.epson-printer-utility.enable = true; } extra ];
  }).config;
  base = eval {};
  active = eval {
    services.epson-printer-utility = {
      users = [ "operator" ];
      device = { serial = "test-serial"; productId = "0081"; selector = "USB:test-serial"; };
      cups.enable = true;
      automaticNozzleCheck = { enable = true; onCalendar = "Mon *-*-* 12:00:00"; };
    };
    users.users.operator.isNormalUser = true;
  };
  network = eval {
    services.epson-printer-utility = { usb.enable = false; device.selector = "192.0.2.1"; };
  };
in
assert !(base.systemd.timers ? epson-nozzle-check);
assert !base.services.printing.enable;
assert base.systemd.services.epson-nozzle-check.serviceConfig.Restart == "no";
assert base.systemd.services.ecbd.serviceConfig.Type == "simple";
assert active.systemd.timers.epson-nozzle-check.timerConfig.Persistent == false;
assert active.users.users.epson-ecbd.group == "epson-maintenance";
assert builtins.elem "epson-maintenance" active.users.users.operator.extraGroups;
assert active.systemd.services.ecbd.environment.EPSON_USB_SERIAL == "test-serial";
assert builtins.elem "epson-maintenance" active.users.users.cups.extraGroups;
assert active.services.printing.enable;
assert builtins.elem active.services.epson-printer-utility.backendPackage active.services.printing.drivers;
assert active.hardware.printers.ensurePrinters == [];
assert !(network.systemd.services ? ecbd);
assert !(nixpkgs.lib.hasInfix "04b8" network.services.udev.extraRules);
assert !(builtins.elem network.services.epson-printer-utility.backendPackage network.environment.systemPackages);
assert !(builtins.elem "ecbd.service" network.systemd.services.epson-nozzle-check.wants);
assert network.systemd.services.epson-nozzle-check.environment.EPSON_CONNECTION == "network";
assert network.networking.firewall.allowedTCPPorts == [];
pkgs.runCommand "epson-module-check" {} ''
  mkdir -p $out
  cp ${base.systemd.units."ecbd.service".unit}/ecbd.service $out/ecbd.service
  cp ${active.systemd.units."epson-nozzle-check.service".unit}/epson-nozzle-check.service $out/epson-nozzle-check.service
  cp ${active.systemd.units."epson-nozzle-check.timer".unit}/epson-nozzle-check.timer $out/epson-nozzle-check.timer
  cp ${network.systemd.units."epson-nozzle-check.service".unit}/epson-nozzle-check.service $out/network-nozzle-check.service
''
