// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef EPSON_NATIVE_REPORT_H
#define EPSON_NATIVE_REPORT_H
#include "EPSPrinterController.h"
#include "BackendLib/backend_api.h"
#include <QJsonArray>
#include <QJsonObject>
#include <QString>
namespace epson {
inline int usbState(int state) {
    switch (state) {
    case ECB_PRNST_IDLE: return EPS_PRNST_IDLE;
    case ECB_PRNST_BUSY: return EPS_PRNST_BUSY;
    case ECB_PRNST_PRINTING: return EPS_PRNST_PRINTING;
    case ECB_PRNST_CANCELLING: return EPS_PRNST_CANCELLING;
    case ECB_PRNST_ERROR: return EPS_PRNST_ERROR;
    default: return -1;
    }
}
inline int usbError(int error) {
    switch (error) {
#define EPSON_USB_ERROR(from, to) case ECB_PRNERR_##from: return EPS_PRNERR_##to;
#include "usb-errors.inc"
#undef EPSON_USB_ERROR
    default: return -1; // Unknown ECB codes must not collide with different EPS meanings.
    }
}
inline const char *stateName(int state) {
    switch (state) {
    case EPS_PRNST_IDLE: return "idle";
    case EPS_PRNST_BUSY: return "busy";
    case EPS_PRNST_PRINTING: return "printing";
    case EPS_PRNST_CANCELLING: return "cancelling";
    case EPS_PRNST_ERROR: return "error";
    default: return "unknown";
    }
}
inline const char *errorName(int error) {
    switch (error) {
#define EPSON_ERROR(code, name) case EPS_PRNERR_##code: return name;
#include "error-names.inc"
#undef EPSON_ERROR
    default: return "unknown-device-error";
    }
}
inline QJsonArray warnings(unsigned mask) {
    const char *names[] = {"paper-low", "maintenance-box-near-end", "maintenance-required", "check-nozzle", "cut-trash-full"};
    QJsonArray out;
    for (unsigned i = 0; i < 5; ++i) if (mask & (1u << i)) out.append(names[i]);
    return out;
}
inline const char *colorName(int id) {
    const char *names[] = {"black", "cyan", "magenta", "yellow", "light-cyan", "light-magenta",
        "light-yellow", "dark-yellow", "light-black", "red", "violet", "matte-black",
        "light-light-black", "photo-black", "clear", "gray", "unknown", "black-2",
        "orange", "green", "white", "clean"};
    return id >= 0 && id < int(sizeof(names)/sizeof(*names)) ? names[id] : "unknown";
}
inline bool inkAvailable(const EPS_INK_INFO &ink, int i) {
    return i >= 0 && i < qBound(0, ink.number, EPS_INK_NUM) && ink.showInkInfo &&
        ink.status[i] >= 0 && ink.remaining[i] >= 0 && ink.remaining[i] <= 100;
}
inline QJsonArray inks(const EPS_INK_INFO &ink) {
    QJsonArray out;
    for (int i = 0; i < qBound(0, ink.number, EPS_INK_NUM); ++i) {
        const bool known = inkAvailable(ink, i);
        out.append(QJsonObject{{"index", i}, {"color", colorName(ink.colors[i])},
            {"label", colorName(ink.colors[i])}, {"device_color_code", ink.colors[i]},
            {"reported_percent", known ? QJsonValue(ink.remaining[i]) : QJsonValue(QJsonValue::Null)},
            {"reported_color_id", ink.colorIdFormat && ink.reportedColorIds[i] >= 0 ? QJsonValue(ink.reportedColorIds[i]) : QJsonValue(QJsonValue::Null)},
            {"color_id_format", ink.colorIdFormat == 1 ? "ink-identifier" : ink.colorIdFormat == 2 ? "st2-type-color" : "unavailable"},
            {"reported_raw", ink.remaining[i]}, {"native_ink_status", ink.status[i]},
            {"source", known ? "device-reported" : ink.showInkInfo ? "device-value-unavailable" : "ink-info-disabled-by-device"}});
    }
    return out;
}
inline QJsonValue count(int value) { return value < 0 ? QJsonValue(QJsonValue::Null) : QJsonValue(value); }
inline qint64 fedTotal(const EPS_PAPER_COUNT &p) {
    return p.color < 0 || p.monochrome < 0 ? -1 : qint64(p.color) + p.monochrome;
}
inline QJsonObject paperCount(const EPS_PAPER_COUNT &p) {
    const qint64 total = fedTotal(p);
    return {{"color", count(p.color)}, {"monochrome", count(p.monochrome)},
        {"blank", count(p.blank)}, {"adf", count(p.adf)},
        {"color_borderless", count(p.color_borderless)}, {"monochrome_borderless", count(p.monochrome_borderless)},
        {"total", total < 0 ? QJsonValue(QJsonValue::Null) : QJsonValue(double(total))},
        {"meaning", "native-paper-feed-counters; not successful-print-pages"}};
}
inline QString printerId(const EPS_PRINTER &p) { return QString::fromLocal8Bit(p.printerID); }
inline QString protocol(const EPS_PRINTER &p) {
    if (p.protocol == EPS_PROTOCOL_USB) return "usb";
    if (EPS_PRT_PROTOCOL(p.protocol) == EPS_PROTOCOL_RAW) return "raw";
    if (EPS_PRT_PROTOCOL(p.protocol) == EPS_PROTOCOL_LPR) return "lpr";
    return "unknown";
}
inline QJsonObject device(const EPS_PRINTER &p) {
    return {{"id", printerId(p)}, {"model", QString::fromLocal8Bit(p.modelName)},
        {"connection", p.protocol == EPS_PROTOCOL_USB ? "usb" : "network"}, {"protocol", protocol(p)},
        {"location", QString::fromLocal8Bit(p.location)}, {"serial", QString::fromLocal8Bit(p.serialNo)}};
}
inline bool matches(const EPS_PRINTER &p, const QString &selector) {
    return selector == "auto" || (selector == "USB" && p.protocol == EPS_PROTOCOL_USB) ||
        selector == printerId(p) || selector == QString::fromLocal8Bit(p.location) ||
        selector == QString::fromLocal8Bit(p.modelName);
}
}
#endif
