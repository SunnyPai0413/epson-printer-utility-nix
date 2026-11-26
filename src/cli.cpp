// SPDX-License-Identifier: GPL-2.0-or-later
#include <QCoreApplication>
#include <QCommandLineParser>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QTextStream>
#include "EPSPrinterController.h"

namespace {
const char *stateName(int state) {
    switch (state) {
    case EPS_PRNST_IDLE: return "idle";
    case EPS_PRNST_BUSY: return "busy";
    case EPS_PRNST_PRINTING: return "printing";
    case EPS_PRNST_CANCELLING: return "cancelling";
    case EPS_PRNST_ERROR: return "error";
    default: return "unknown";
    }
}
const char *errorName(int error) {
    switch (error) {
    case EPS_PRNERR_NOERROR: return "none";
    case EPS_PRNERR_PAPEROUT: return "paper-out";
    case EPS_PRNERR_PAPERJAM: return "paper-jam";
    case EPS_PRNERR_INKOUT: return "ink-out";
    case EPS_PRNERR_COVEROPEN: return "cover-open";
    default: return "device-error";
    }
}
QJsonArray sixInks(const EPS_INK_INFO &ink) {
    // Use Epson color IDs, including its photo/matte black variants; never slot order.
    const char *keys[] = {"black", "cyan", "magenta", "yellow", "light-cyan", "light-magenta"};
    const char *labels[] = {"黑", "青", "品红", "黄", "浅青", "浅品红"};
    QJsonArray out;
    for (int color = 0; color < 6; ++color) {
        QJsonValue value = QJsonValue::Null;
        QString reason = "missing-color-id";
        int matches = 0;
        QJsonValue deviceColor = QJsonValue::Null, raw = QJsonValue::Null, nativeStatus = QJsonValue::Null;
        for (int i = 0; i < qBound(0, ink.number, EPS_INK_NUM); ++i) {
            const int id = ink.colors[i];
            const bool black = color == EPS_COLOR_BLACK &&
                (id == EPS_COLOR_PHOTOBLACK || id == EPS_COLOR_MATTEBLACK || id == EPS_COLOR_BLACK2);
            if (id != color && !black) continue;
            ++matches;
            deviceColor = id; raw = ink.remaining[i]; nativeStatus = ink.status[i];
            reason = ink.showInkInfo ? "device-value-unavailable" : "ink-info-disabled-by-device";
            if (ink.showInkInfo && ink.status[i] >= 0 && ink.remaining[i] >= 0 && ink.remaining[i] <= 100) {
                value = ink.remaining[i]; reason = "device-reported";
            }
        }
        if (matches > 1) { value = QJsonValue::Null; reason = "ambiguous-color-id"; }
        out.append(QJsonObject{{"color", keys[color]}, {"label", QString::fromUtf8(labels[color])},
                               {"reported_percent", value}, {"source", reason}, {"device_color_code", deviceColor},
                               {"reported_raw", raw}, {"native_ink_status", nativeStatus}});
    }
    return out;
}
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    app.setApplicationName("epson-printer-cli");
    app.setApplicationVersion("1.1.3");
    QCommandLineParser args;
    args.setApplicationDescription("Native Epson USB utility. Values are device reports, not actual liquid levels.");
    args.addHelpOption(); args.addVersionOption();
    args.addPositionalArgument("command", "status | ink | nozzle-check | clean");
    QCommandLineOption device("device", "Exact discovered model name (including '(USB)'), USB, or auto (one matching printer).", "selector", "auto");
    QCommandLineOption json("json", "Emit JSON, including null for unknown ink values.");
    QCommandLineOption scheduled("scheduled", "For nozzle-check only: log skips, return success, never retry or queue.");
    QCommandLineOption confirm("confirm-clean", "Explicitly authorize one ordinary head cleaning.");
    args.addOptions({device, json, scheduled, confirm});
    args.process(app);
    const QStringList commands = {"status", "ink", "nozzle-check", "clean"};
    const QString command = args.positionalArguments().value(0);
    if (args.positionalArguments().size() != 1 || !commands.contains(command) ||
        (args.isSet(scheduled) && command != "nozzle-check") ||
        (command == "clean" && !args.isSet(confirm))) {
        QTextStream(stderr) << "Expected one of status, ink, nozzle-check, clean. clean requires --confirm-clean.\n";
        return 2;
    }
    const bool maintenance = command == "nozzle-check" || command == "clean";
    QJsonObject result{{"command", command}, {"device", args.value(device)}, {"status", "unknown"},
                       {"error", "unknown"}, {"outcome", "unknown"}};
    EPS_INK_INFO ink = {};
    auto finish = [&](const QString &outcome, const QString &reason, int code) {
        result["outcome"] = outcome; result["reason"] = reason;
        if (command == "ink") result["ink"] = sixInks(ink);
        if (args.isSet(json)) {
            QTextStream(stdout) << QJsonDocument(result).toJson(QJsonDocument::Compact) << '\n';
        } else {
            QTextStream out(stdout);
            out << "device=" << result["device"].toString() << " status=" << result["status"].toString()
                << " error=" << result["error"].toString() << " outcome=" << outcome << " reason=" << reason << '\n';
            if (command == "ink") {
                for (const auto entry : sixInks(ink)) {
                    const auto row = entry.toObject();
                    out << row["label"].toString() << " (" << row["color"].toString() << "): ";
                    if (row["reported_percent"].isNull()) out << QString::fromUtf8("未知");
                    else out << row["reported_percent"].toInt() << "% (device-reported)";
                    out << '\n';
                }
                out << "Device-reported values; these are not measurements of actual liquid levels.\n";
            }
        }
        EPSPrinterController::ReleaseInstance();
        return code;
    };
    auto skip = [&](const QString &reason) {
        return finish(maintenance ? "skipped" : "unavailable", reason, args.isSet(scheduled) ? 0 : 3);
    };
    EPSPrinterController *controller = EPSPrinterController::GetInstance();
    if (!controller->InitializeCommonLib()) return skip("initialization-failed");
    controller->StartFindPrinter();
    QVector<EPS_PRINTER> matches;
    for (const auto &printer : controller->GetPrinterList()) {
        if (printer.protocol != EPS_PROTOCOL_USB) continue;
        const QString name = QString::fromLocal8Bit(printer.modelName);
        if (args.value(device) == "auto" || args.value(device) == "USB" || args.value(device) == name)
            matches.append(printer);
    }
    if (matches.isEmpty()) return skip("offline-or-device-not-matched");
    if (matches.size() != 1) return skip("ambiguous-device");
    const auto printer = matches.first();
    result["device"] = QString::fromLocal8Bit(printer.modelName);
    if (!controller->ConnectToPrinter(result["device"].toString(), QString::fromLocal8Bit(printer.printerID)))
        return skip("connect-failed");
    EPS_STATUS status = {};
    if (!controller->GetCurrentPrinterStatus(&status, &ink)) return skip("status-unavailable");
    result["status"] = stateName(status.printerStatus);
    result["error"] = errorName(status.errorCode);
    result["status_code"] = status.printerStatus;
    result["error_code"] = status.errorCode;
    if (!maintenance) return finish("reported", "device-reported", 0);
    if (status.errorCode == EPS_PRNERR_PAPEROUT) return skip("paper-out");
    if (status.printerStatus != EPS_PRNST_IDLE) return skip(stateName(status.printerStatus));
    if (status.errorCode != EPS_PRNERR_NOERROR) return skip(errorName(status.errorCode));
    // The controller obtains the shared GUI/CLI lock and checks status again.
    const EPS_ERR_CODE code = command == "clean" ? controller->HeadCleanPrinter() : controller->NozzleCheckPrinter();
    result["native_result"] = code;
    if (code == EPS_ERR_PRINTER_NOT_USEFUL) return skip("lock-unavailable-or-device-no-longer-idle");
    if (code != EPS_ERR_NONE)
        return finish("unconfirmed", "native-command-or-follow-up-status-unconfirmed; no retry", args.isSet(scheduled) ? 0 : 4);
    return finish("submitted", "one native command sent; physical result requires human confirmation", 0);
}
