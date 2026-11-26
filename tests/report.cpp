// SPDX-License-Identifier: GPL-2.0-or-later
// Shared reports, selection, and explicit USB->EPS enum mapping without hardware.
#include "native-report.h"
#include <cstdlib>
#include <cstring>
static void require(bool condition) { if (!condition) std::abort(); }
int main() {
    require(epson::usbState(ECB_PRNST_BUSY) == EPS_PRNST_BUSY);
    require(epson::usbState(ECB_PRNST_PRINTING) == EPS_PRNST_PRINTING);
#define EPSON_USB_ERROR(from, to) require(epson::usbError(ECB_PRNERR_##from) == EPS_PRNERR_##to);
#include "usb-errors.inc"
#undef EPSON_USB_ERROR
    require(epson::usbError(ECB_PRNERR_MAINTE_REQUIRED) != EPS_PRNERR_CDRGUIDEOPEN);
    require(epson::usbError(999) == -1);
    require(epson::warnings(0x1f).size() == 5);
    EPS_INK_INFO ink = {};
    require(epson::inks(ink).isEmpty());
    ink.number = 8; ink.showInkInfo = 1;
    const int colors[] = {EPS_COLOR_PHOTOBLACK, EPS_COLOR_MATTEBLACK, EPS_COLOR_BLACK2, EPS_COLOR_CYAN,
        EPS_COLOR_ORANGE, EPS_COLOR_GRAY, EPS_COLOR_UNKNOWN, EPS_COLOR_CYAN};
    for (int i = 0; i < 8; ++i) { ink.colors[i] = colors[i]; ink.remaining[i] = i; }
    auto result = epson::inks(ink);
    require(result.size() == 8);
    require(result[0].toObject()["color"].toString() == "photo-black");
    require(result[1].toObject()["color"].toString() == "matte-black");
    require(result[2].toObject()["color"].toString() == "black-2");
    require(result[0].toObject()["reported_percent"].toInt(-1) == 0);
    require(result[3].toObject()["reported_percent"].toInt(-1) == 3);
    require(result[7].toObject()["reported_percent"].toInt(-1) == 7); // preserve duplicate entries
    ink.remaining[0] = 105; ink.status[1] = -3;
    require(epson::inks(ink)[0].toObject()["reported_percent"].isNull());
    require(epson::inks(ink)[1].toObject()["reported_percent"].isNull());
    ink.showInkInfo = 0;
    for (auto v : epson::inks(ink)) require(v.toObject()["reported_percent"].isNull());
    EPS_PAPER_COUNT p = {-1, -1, -1, -1, -1, -1};
    require(epson::paperCount(p)["total"].isNull());
    p.color = 20; require(epson::paperCount(p)["total"].isNull());
    p.monochrome = 0; require(epson::fedTotal(p) == 20);
    p.color = 2147483647; p.monochrome = 2147483647;
    require(epson::fedTotal(p) == 4294967294LL);
    EPS_PRINTER printer = {}; printer.protocol = EPS_PROTOCOL_USB;
    strcpy(printer.printerID, "USB:serial"); strcpy(printer.modelName, "Test (USB)");
    require(epson::matches(printer, "USB:serial") && epson::matches(printer, "USB"));
    require(!epson::matches(printer, "wrong-id"));
    printer.protocol = EPS_PROTOCOL_LPR; strcpy(printer.printerID, "native-network-id");
    strcpy(printer.location, "192.0.2.1");
    require(epson::matches(printer, "native-network-id") && epson::matches(printer, "192.0.2.1"));
    require(!epson::matches(printer, "USB"));
}
