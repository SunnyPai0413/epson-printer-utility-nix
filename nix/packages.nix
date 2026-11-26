{ pkgs }:
let
  inherit (pkgs) lib;
  source = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [ ../CMakeLists.txt ../VERSION ../NOTICE.md ../LICENSE ../LICENSES ../CHANGELOG.md ../src
      (lib.fileset.fileFilter (file: file.hasExt "py") ../patches)
      (lib.fileset.fileFilter (file: file.hasExt "cpp" || file.hasExt "py" || file.hasExt "nix") ../tests) ../upstream/rpm/epson-printer-utility.tar.gz ../upstream/rpm/epson-backend.tar.gz ];
  };
  common = {
    version = lib.removeSuffix "\n" (builtins.readFile ../VERSION);
    src = source;
    nativeBuildInputs = [ pkgs.cmake pkgs.pkg-config pkgs.python3 ];
    postUnpack = ''
      tar -xzf "$sourceRoot/upstream/rpm/epson-printer-utility.tar.gz" -C "$sourceRoot"
      tar -xzf "$sourceRoot/upstream/rpm/epson-backend.tar.gz" -C "$sourceRoot"
    '';
    passthru.upstreamVersions = { utility = "1.1.3"; backend = "1.3.1"; };
    postPatch = ''python3 patches/adapt.py'';
    meta = {
      description = "Epson's native printer utility with a USB/network GUI and maintenance CLI";
      homepage = "https://github.com/SunnyPai0413/epson-printer-utility-nix";
      changelog = "https://github.com/SunnyPai0413/epson-printer-utility-nix/blob/main/CHANGELOG.md";
      license = with lib.licenses; [ gpl2Plus lgpl21Plus ];
      platforms = lib.platforms.linux;
    };
  };
  backend = pkgs.stdenv.mkDerivation (common // {
    pname = "epson-backend";
    buildInputs = [ pkgs.libusb1 ];
    doCheck = true;
    cmakeFlags = [ "-DBUILD_UTILITY=OFF" ];
    meta = common.meta // { mainProgram = "ecbd"; };
  });
  utility = pkgs.stdenv.mkDerivation (common // {
    pname = "epson-printer-utility";
    nativeBuildInputs = common.nativeBuildInputs ++ [ pkgs.qt5.wrapQtAppsHook ];
    buildInputs = [ pkgs.qt5.qtbase pkgs.libjpeg ];
    cmakeFlags = [ "-DBUILD_BACKEND=OFF" ];
    doCheck = true;
    meta = common.meta // { mainProgram = "epson-printer-utility"; };
  });
in {
  epson-printer-utility = utility;
  epson-backend = backend;
  ecblp = backend; # services.printing.drivers package, not a raster/filter driver
  default = pkgs.symlinkJoin { name = "epson-utility-suite-${utility.version}"; paths = [ utility backend ]; };
}
