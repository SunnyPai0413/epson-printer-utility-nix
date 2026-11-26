// SPDX-License-Identifier: GPL-2.0-or-later
#include <QCoreApplication>
#include <QCommandLineParser>
#include <QJsonDocument>
#include <QTextStream>
#include "native-report.h"

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    app.setApplicationName("epson-printer-cli");
    app.setApplicationVersion(EPSON_PROJECT_VERSION);
    QCommandLineParser args;
    args.setApplicationDescription("Native Epson USB/network utility. Ink values are device reports, not measured liquid levels.");
    args.addHelpOption(); args.addVersionOption();
    args.addPositionalArgument("command", "devices | status | ink | paper-count | nozzle-check | clean");
    QCommandLineOption device("device", "Native discovered ID or address, exact model, USB, or auto (one matching printer).", "selector", "auto");
    QCommandLineOption connection("connection", "Discovery scope: all, usb, network. USB selectors default to usb.", "scope");
    QCommandLineOption json("json", "Emit schema 2 JSON; unknown values are null or an empty ink list.");
    QCommandLineOption scheduled("scheduled", "For nozzle-check only: skip offline/busy/locked devices, never retry or queue.");
    QCommandLineOption confirm("confirm-clean", "Explicitly authorize one ordinary head cleaning.");
    args.addOptions({device, connection, json, scheduled, confirm});
    args.process(app);
    const QStringList commands = {"devices", "status", "ink", "paper-count", "nozzle-check", "clean"};
    const QString command = args.positionalArguments().value(0);
    QString scope = args.isSet(connection) ? args.value(connection) : QString::fromLocal8Bit(qgetenv("EPSON_CONNECTION"));
    if (scope.isEmpty()) scope = args.value(device).startsWith("USB") ? "usb" : "all";
    if (args.positionalArguments().size() != 1 || !commands.contains(command) ||
        !QStringList({"all", "usb", "network"}).contains(scope) ||
        (args.isSet(scheduled) && command != "nozzle-check") ||
        (command == "clean" && !args.isSet(confirm))) {
        QTextStream(stderr) << "Expected devices, status, ink, paper-count, nozzle-check, or clean. clean requires --confirm-clean; --connection is all, usb, or network.\n";
        return 2;
    }
    qputenv("EPSON_CONNECTION", scope.toLocal8Bit());
    const bool maintenance = command == "nozzle-check" || command == "clean";
    QJsonObject result{{"schema_version", 2}, {"project_version", EPSON_PROJECT_VERSION},
        {"upstream_utility_version", "1.1.3"}, {"upstream_backend_version", "1.3.1"},
        {"command", command}, {"device", args.value(device)}, {"status", "unknown"},
        {"error", "unknown"}, {"communication", "unknown"}, {"warnings", QJsonArray()}, {"outcome", "unknown"}};
    EPS_INK_INFO ink = {};
    auto finish = [&](const QString &outcome, const QString &reason, int code) {
        result["outcome"] = outcome; result["reason"] = reason;
        if (command == "ink") result["ink"] = epson::inks(ink);
        if (args.isSet(json)) {
            QTextStream(stdout) << QJsonDocument(result).toJson(QJsonDocument::Compact) << '\n';
        } else {
            QTextStream out(stdout);
            out << "device=" << result["device"].toString() << " status=" << result["status"].toString()
                << " error=" << result["error"].toString() << " outcome=" << outcome << " reason=" << reason << '\n';
            for (auto v : result["warnings"].toArray()) out << "warning=" << v.toString() << '\n';
            if (command == "devices") for (auto entry : result["devices"].toArray()) {
                const auto row = entry.toObject();
                out << row["id"].toString() << '\t' << row["model"].toString() << '\t' << row["location"].toString() << '\n';
            }
            if (command == "ink") {
                if (ink.number == 0) out << "Ink: unknown (no color IDs available)\n";
                for (auto entry : epson::inks(ink)) {
                    const auto row = entry.toObject();
                    out << row["color"].toString() << " [ID " << row["device_color_code"].toInt() << "]: ";
                    if (row["reported_percent"].isNull()) out << "unknown";
                    else out << row["reported_percent"].toInt() << "% (device-reported)";
                    out << '\n';
                }
            }
            if (command == "paper-count") out << QJsonDocument(result["paper_count"].toObject()).toJson(QJsonDocument::Compact) << '\n';
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
    QJsonArray devices;
    for (const auto &printer : controller->GetPrinterList()) {
        if (!epson::matches(printer, args.value(device))) continue;
        matches.append(printer); devices.append(epson::device(printer));
    }
    if (command == "devices") { result["devices"] = devices; return finish("reported", "discovery-complete", 0); }
    if (matches.isEmpty()) return skip("offline-or-device-not-matched");
    if (matches.size() != 1) return skip("ambiguous-device");
    const auto printer = matches.first();
    result["device"] = QString::fromLocal8Bit(printer.modelName);
    result["device_info"] = epson::device(printer);
    auto communicationFailure = [&](const QString &reason) {
        result["communication"] = "failed"; result["error"] = "communication-error";
        return skip(reason);
    };
    if (!controller->ConnectToPrinter(result["device"].toString(), epson::printerId(printer)))
        return communicationFailure("connect-failed");
    EPS_STATUS status = {};
    if (!controller->GetCurrentPrinterStatus(&status, &ink)) return communicationFailure("status-unavailable");
    result["communication"] = "ok";
    result["status"] = epson::stateName(status.printerStatus);
    result["error"] = epson::errorName(status.errorCode);
    result["status_code"] = status.printerStatus;
    result["error_code"] = status.errorCode;
    result["warnings"] = epson::warnings(status.warnings);
    result["warning_mask"] = int(status.warnings);
    result["paper_count"] = epson::paperCount(status.paper_count);
    if (command == "paper-count") {
        bool available = false;
        for (const auto value : result["paper_count"].toObject()) if (value.isDouble()) available = true;
        return available ? finish("reported", "device-reported-feed-counters", 0) : skip("paper-count-not-supported-or-unavailable");
    }
    if (!maintenance) return finish("reported", "device-reported", 0);
    if (status.errorCode == EPS_PRNERR_PAPEROUT) return skip("paper-out");
    if (status.printerStatus != EPS_PRNST_IDLE) return skip(epson::stateName(status.printerStatus));
    if (status.errorCode != EPS_PRNERR_NOERROR) return skip(epson::errorName(status.errorCode));
    const EPS_ERR_CODE code = controller->MaintainPrinter(result["device"].toString(), epson::printerId(printer), command == "clean");
    result["native_result"] = code;
    if (code == EPS_ERR_PRINTER_NOT_USEFUL) return skip("lock-unavailable-or-device-no-longer-idle");
    if (code != EPS_ERR_NONE)
        return finish("unconfirmed", "native-command-or-follow-up-status-unconfirmed; no retry", args.isSet(scheduled) ? 0 : 4);
    return finish("submitted", "one native command sent; physical result requires human confirmation", 0);
}
