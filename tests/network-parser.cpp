// SPDX-License-Identifier: GPL-2.0-or-later
// Epson's native network status parser, binary field fixtures only (no printer).
#include "native-report.h"
#include "escpr-lib/inc/epson-escpr-pvt.h"
#include "escpr-lib/inc/epson-escpr-services.h"
#include <QByteArray>
#include <cstdlib>
#include <cstdio>
#define require(v) do { if (!(v)) { fprintf(stderr, "network parser assertion at line %d: %s\n", __LINE__, #v); std::abort(); } } while (0)
static void field(QByteArray &packet, int code, const QByteArray &value) {
    packet.append(char(code)); packet.append(char(value.size())); packet += value;
}
static EPS_STATUS_INFO parse(QByteArray fields) {
    QByteArray packet("@BDC ST2\r\n", 10);
    packet.append(char(fields.size())); packet.append(char(fields.size() >> 8)); packet += fields;
    packet.append('\0');
    EPS_STATUS_INFO info = {};
    require(serAnalyzeStatus(packet.data(), 0, &info) == EPS_ERR_NONE);
    return info;
}
int main() {
    QByteArray fields;
    field(fields, 1, QByteArray(1, 4)); // idle
    field(fields, 4, QByteArray::fromHex("00202145B0"));
    auto info = parse(fields);
    require(info.nError == EPS_PRNERR_NOERROR && info.warnings == 31);
    require(info.nInkNo == 0 && info.paper_count.color == -1 && !info.showInkInfo);
    field(fields, 2, QByteArray(1, 0x41));
    info = parse(fields);
    require(info.nError == EPS_PRNERR_MAINTE_REQUIRED && info.warnings == 31);
    fields.clear();
    field(fields, 1, QByteArray(1, 4));
    field(fields, 0x0a, QByteArray::fromHex("1000"));
    field(fields, 0x0f, QByteArray::fromHex("030B0000030169030220"));
    QByteArray counts(32, 0);
    counts[8] = 1; counts[9] = 2; counts[10] = 3; counts[11] = 4;
    counts[24] = 5; counts[25] = 6; counts[26] = 7; counts[27] = 8;
    field(fields, 0x36, counts);
    info = parse(fields);
    require(info.warnings == 0 && info.nInkNo == 3 && info.showInkInfo);
    require(info.colorIdFormat == 2 && info.reportedColorIds[0] == 0x0B00);
    require(info.nColorType[0] == EPS_COLOR_MATTEBLACK && info.nColor[0] == 0);
    require(info.nColorType[1] == EPS_COLOR_CYAN && info.nColorStatus[1] == EPS_INK_ST_NOREAD);
    require(info.paper_count.color == 0x04030201 && info.paper_count.color_borderless == 0x08070605);
}
