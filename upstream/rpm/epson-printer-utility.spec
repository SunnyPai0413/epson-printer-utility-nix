#Copyright (C) Seiko Epson Corporation 2017.
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public
#License along with this program; if not, write to the Free  Software Foundation, Inc., 
#51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

%define packagename     epson-printer-utility
%define pkgver    		1.1.3
%define utility_name	epson-printer-utility
%define utility_ver		1.1.3
%define backend_name	epson-backend	
%define backend_ver		1.3.1

%define rel     		1
%define extraversion    -%{rel}

%define supplier		%{packagename}
%define supplierstr     Seiko Epson Corporation


AutoReqProv: no

Name: %{packagename}
Version: %{pkgver}
Release: %{rel}
Source0: %{name}.tar.gz
Source1: %{backend_name}.tar.gz
License: LGPL
Vendor: %{supplierstr}
URL: http://download.ebz.epson.net/dsc/search/01/search/?OSC=LX
Packager: Seiko Epson Corporation <linux-printer@epson.jp>
BuildRoot: %{_tmppath}/%{packagename}-%{pkgver}-%{release}
Group: Applications/System
#Requires:
Summary: Epson Printer Utility for Linux

%description
This is a Printer Utility program for Epson Printer Driver.  
Using this software, you can check ink levels, view error and other status... on EPSON Printers. 
For detail list of supported printer, please refer to below site:
http://download.ebz.epson.net/dsc/search/01/search/?OSC=LX

%prep
rm -rf %{buildroot}
rm -rf $RPM_BUILD_DIR/%{packagename}-%{pkgver}
tar xzvf %{_sourcedir}/%{backend_name}.tar.gz -C $RPM_BUILD_DIR/
tar xzvf %{_sourcedir}/%{utility_name}.tar.gz -C $RPM_BUILD_DIR/

%build
# backend
cd %{backend_name}
touch m4-macros
autoreconf -vfi
./configure
make

# utility
cd ../%{utility_name}
autoreconf -vfi
./configure --prefix=/opt/epson-printer-utility
# make clean
make

%install
# rm -rf %{buildroot}
# Make directories
# utility
cd %{packagename}
ls
# install -d %{buildroot}%{_libdir}
make install-strip DESTDIR=${RPM_BUILD_ROOT}

rules_dir=/etc/udev/rules.d

install -d %{buildroot}%{_docdir}
install -m 755 README AUTHORS NEWS INSTALL ChangeLog %{buildroot}%{_docdir}
install -m 0755 epson-printer-utility.desktop %{buildroot}/opt/epson-printer-utility/

cd PrinterUtility
install -d %{buildroot}/opt/epson-printer-utility/bin
install -m 0777 %{utility_name} %{buildroot}/opt/epson-printer-utility/bin

install -d %{buildroot}/opt/epson-printer-utility/resource
cp -R Images %{buildroot}/opt/epson-printer-utility/resource

cd ..
cd EPSCommonLib
install -d %{buildroot}/opt/epson-printer-utility/lib
install -m 0755 libEPSCommonLib.a %{buildroot}/opt/epson-printer-utility/lib
cd ..
cd support-tool
install -d %{buildroot}/opt/epson-printer-utility/rules
install -m 0755 79-udev-epson.rules %{buildroot}/opt/epson-printer-utility/rules
cd ..

# backend
cd ../%{backend_name}
install -d %{buildroot}/usr/lib/cups/backend
install -m 755 src/ecblp %{buildroot}/usr/lib/cups/backend/ecblp

install -d %{buildroot}/usr/lib/%{backend_name}
install -m 755 daemon/ecbd %{buildroot}/usr/lib/%{backend_name}/ecbd
install -m 644 daemon/ecbd.service %{buildroot}/usr/lib/%{backend_name}/ecbd.service
install -m 644 daemon/ecbd.conf %{buildroot}/usr/lib/%{backend_name}/ecbd.conf
install -m 644 daemon/ecbd.pp %{buildroot}/usr/lib/%{backend_name}/ecbd.pp
install -m 644 daemon/ecblp.pp %{buildroot}/usr/lib/%{backend_name}/ecblp.pp

install -d %{buildroot}/usr/lib/%{backend_name}/rc.d/
install -m 755 daemon/rc/ecbd           %{buildroot}/usr/lib/%{backend_name}/rc.d/ecbd
install -m 755 daemon/rc/init-functions %{buildroot}/usr/lib/%{backend_name}/rc.d/init-functions
install -m 755 daemon/rc/inst-rc_d.sh   %{buildroot}/usr/lib/%{backend_name}/rc.d/inst-rc_d.sh

install -d %{buildroot}/usr/lib/%{backend_name}/scripts/
install -m 755 setup/inst-cups-post.sh %{buildroot}/usr/lib/%{backend_name}/scripts/inst-cups-post.sh

install -m 755 selinux/epson_pol.pp %{buildroot}/usr/lib/%{backend_name}/epson_pol.pp

%pre

%post
/sbin/ldconfig
# utility
ln -s /opt/%{packagename}/bin/%{utility_name} /usr/bin/%{utility_name}
install -m 0755 /opt/epson-printer-utility/rules/79-udev-epson.rules /etc/udev/rules.d
install -m 0755 /opt/epson-printer-utility/epson-printer-utility.desktop /usr/share/applications

# backend
cd /usr/lib/%{backend_name}/scripts/
./inst-cups-post.sh install
cd /usr/lib/%{backend_name}
if command -v semodule > /dev/null 2>&1;then
	semodule -i epson_pol.pp
fi

%preun
if [ "$1" = 0 ] ; then
	 cd /usr/lib/%{backend_name}/scripts/
        ./inst-cups-post.sh deinstall
        rm -f /usr/lib/%{name}/setup
fi

%postun
/sbin/ldconfig
rm -f /usr/bin/%{utility_name}
rm -f /etc/udev/rules.d/79-udev-epson.rules
rm -f /usr/share/applications/epson-printer-utility.desktop
rm -f /opt/epson-printer-utility/lib/*
rm -f /usr/lib/%{backend_name}/setup
if command -v semodule > /dev/null 2>&1;then
	semodule -r epson_pol
fi

#rm -r /opt/%{utility_name}
#rm -r /usr/lib/epson-backend

%clean
cd $RPM_BUILD_DIR/%{packagename}
make clean
#rm -rf %{buildroot}

%files
%defattr(-,root,root)
/opt/epson-printer-utility/bin/epson-printer-utility
/opt/epson-printer-utility/lib/libEPSCommonLib.a
/opt/epson-printer-utility/resource/Images/*
/opt/epson-printer-utility/resource/Languages/*
/opt/epson-printer-utility/rules/79-udev-epson.rules
/opt/epson-printer-utility/epson-printer-utility.desktop
/usr/lib/cups/backend/ecblp
/usr/lib/epson-backend/ecbd
/usr/lib/epson-backend/rc.d/ecbd
/usr/lib/epson-backend/ecbd.conf
/usr/lib/epson-backend/ecbd.service
/usr/lib/epson-backend/rc.d/init-functions
/usr/lib/epson-backend/rc.d/inst-rc_d.sh
/usr/lib/epson-backend/scripts/inst-cups-post.sh
/usr/lib/epson-backend/epson_pol.pp
/usr/lib/epson-backend/ecbd.pp
/usr/lib/epson-backend/ecblp.pp
/usr/share/doc/AUTHORS
/usr/share/doc/ChangeLog
/usr/share/doc/INSTALL
/usr/share/doc/NEWS
/usr/share/doc/README



