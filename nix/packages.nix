{ pkgs }:
let
  inherit (pkgs) lib;
  source = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [ ../CMakeLists.txt ../src ../patches ../tests ../upstream/rpm/epson-printer-utility.tar.gz ../upstream/rpm/epson-backend.tar.gz ];
  };
  common = {
    version = "1.1.3";
    src = source;
    nativeBuildInputs = [ pkgs.cmake pkgs.pkg-config pkgs.python3 ];
    postUnpack = ''
      tar -xzf "$sourceRoot/upstream/rpm/epson-printer-utility.tar.gz" -C "$sourceRoot"
      tar -xzf "$sourceRoot/upstream/rpm/epson-backend.tar.gz" -C "$sourceRoot"
    '';
    postPatch = ''python3 patches/adapt.py'';
    meta = {
      description = "Epson's native printer utility with a restricted USB maintenance CLI";
      homepage = "https://download.ebz.epson.net/dsc/search/01/search/?OSC=LX";
      license = with lib.licenses; [ gpl2Plus lgpl21Plus ];
      platforms = lib.platforms.linux;
    };
  };
  backend = pkgs.stdenv.mkDerivation (common // {
    pname = "epson-backend";
    version = "1.3.1";
    buildInputs = [ pkgs.libusb1 ];
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
  default = pkgs.symlinkJoin { name = "epson-utility-suite-1.1.3"; paths = [ utility backend ]; };
}
