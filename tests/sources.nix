# SPDX-License-Identifier: GPL-2.0-or-later
{ pkgs }:
pkgs.runCommand "epson-source-integrity" {} ''
  mkdir sources
  cd sources
  ln -s ${../upstream/epson-printer-utility-1.1.3-1.src.rpm} epson-printer-utility-1.1.3-1.src.rpm
  mkdir rpm
  ln -s ${../upstream/rpm/epson-printer-utility.tar.gz} rpm/epson-printer-utility.tar.gz
  ln -s ${../upstream/rpm/epson-backend.tar.gz} rpm/epson-backend.tar.gz
  ln -s ${../upstream/rpm/epson-printer-utility.spec} rpm/epson-printer-utility.spec
  sed 's@  upstream/@  @' ${../upstream/SHA256SUMS} | sha256sum -c -
  mkdir $out
  cp ${../upstream/SHA256SUMS} $out/SHA256SUMS
''
