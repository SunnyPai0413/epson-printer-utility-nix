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
      device = { serial = "test-serial"; productId = "0081"; model = "L805 Series (USB)"; };
      automaticNozzleCheck = { enable = true; onCalendar = "Mon *-*-* 12:00:00"; };
    };
    users.users.operator.isNormalUser = true;
  };
in
assert !(base.systemd.timers ? epson-nozzle-check);
assert base.systemd.services.epson-nozzle-check.serviceConfig.Restart == "no";
assert base.systemd.services.ecbd.serviceConfig.Type == "simple";
assert active.systemd.timers.epson-nozzle-check.timerConfig.Persistent == false;
assert active.users.users.epson-ecbd.group == "epson-maintenance";
assert builtins.elem "epson-maintenance" active.users.users.operator.extraGroups;
assert active.systemd.services.ecbd.environment.EPSON_USB_SERIAL == "test-serial";
pkgs.runCommand "epson-module-check" {} ''
  mkdir -p $out
  cp ${base.systemd.units."ecbd.service".unit}/ecbd.service $out/ecbd.service
  cp ${active.systemd.units."epson-nozzle-check.service".unit}/epson-nozzle-check.service $out/epson-nozzle-check.service
  cp ${active.systemd.units."epson-nozzle-check.timer".unit}/epson-nozzle-check.timer $out/epson-nozzle-check.timer
''
