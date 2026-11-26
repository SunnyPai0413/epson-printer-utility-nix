#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Small, asserted edits to the local 1.1.3/1.3.1 sources; never downloads code."""
from pathlib import Path
import re
U = Path('epson-printer-utility')
B = Path('epson-backend')
MODIFICATION_DATE = '2026-11-26'
original_files = {}
def edit(path, fn):
    original_files.setdefault(path, path.read_bytes())
    s = path.read_text(encoding='utf-8-sig')
    path.write_text(fn(s))
def replace(s, old, new):
    assert old in s, old[:100]
    return s.replace(old, new)

# Original GUI, resources from the immutable package, user settings via XDG.
def main(s):
    s = replace(s, '#include <QLocale>', '#include <QLocale>\n#include <QStandardPaths>\n#include <QDir>')
    s = replace(s, 'QString current_langfile = "/opt/epson-printer-utility/resource/Languages/";',
                'QString current_langfile = QString::fromUtf8(EPSON_RESOURCE_DIR) + "/";')
    s = replace(s, 'current_langfile += locale;', 'current_langfile += QLocale::system().name();')
    start = s.index('//Make Save Directory')
    end = s.index('//Read ini File', start)
    s = s[:start] + '''const QString settingsDir = QStandardPaths::writableLocation(QStandardPaths::AppConfigLocation);
    QDir().mkpath(settingsDir);
    const QByteArray settingsFile = QFile::encodeName(settingsDir + "/utility.ini");
    const char *ini_file = settingsFile.constData();

''' + s[end:]
    return s.replace('#include <QDir>', '#include <QDir>\n#include <QFile>')
edit(U/'PrinterUtility/Main.cpp', main)

# Restore native network discovery; USB remains on BackendLib/ecbd.
def communicator(s):
    s = replace(s, '\t \tprintf (\"Communication daemon down, Error code = %d\\n\", ret2 );', '\t \tqWarning(\"ecbd unavailable; start ecbd.service\");')
    s = replace(s, '\t\texit(1);', '\t\t// USB is optional; native network remains available.')
    s = replace(s, 'ECB_STATUS status_usb;', 'ECB_STATUS status_usb = {};')
    s = '#include "native-report.h"\n' + s
    s = replace(s, 'status->printerStatus = status_usb.printerStatus;', 'status->printerStatus = epson::usbState(status_usb.printerStatus);')
    s = replace(s, 'status->errorCode = status_usb.errorCode;', 'status->errorCode = epson::usbError(status_usb.errorCode);\n            status->warnings = status_usb.warnings;')
    s = replace(s, 'inkInfo->number= status_usb.ink_num;', 'inkInfo->number = qBound(0, status_usb.ink_num, EPS_INK_NUM);')
    s = replace(s, 'i < status_usb.ink_num', 'i < inkInfo->number')
    s = replace(s, 'inkInfo->status[i]=EPS_INK_ST_NORMAL; //not used in this STM', 'inkInfo->status[i]=status_usb.inkstatus[i];')
    return s
edit(U/'EPSCommonLib/EPSCommunicator.cpp', communicator)

# All GUI and CLI maintenance uses one nonblocking lock, then a fresh status check.
# Keep the lock while the device completes, never resend a maintenance command.
def controller(s):
    s = replace(s, '#include <QDebug>', '#include <QDebug>\n#include <QThread>\n#include "operation-lock.h"')
    pos = s.index('EPS_ERR_CODE EPSPrinterController::NozzleCheckPrinter()')
    end = s.index('bool EPSPrinterController::ConnectToPrinter', pos)
    s = s[:pos] + '''static EPS_ERR_CODE guardedMaintenance(bool clean) {
    int lock = epson_operation_lock(0);
    if (lock < 0) return EPS_ERR_PRINTER_NOT_USEFUL;
    EPSCommunicator *c = EPSCommunicator::GetInstance();
    EPS_STATUS status = {}; EPS_INK_INFO ink = {};
    EPS_ERR_CODE result = EPS_ERR_PRINTER_NOT_USEFUL;
    if (c->GetCurrentPrinterStatus(&status, &ink) &&
        status.printerStatus == EPS_PRNST_IDLE && status.errorCode == EPS_PRNERR_NOERROR) {
        result = clean ? c->HeadCleanPrinter() : c->NozzleCheckPrinter();
        if (result == EPS_ERR_NONE) {
            // Allow time for the command to leave the FIFO, then wait for idle.
            // A timeout means outcome unknown; it never causes a second command.
            QThread::sleep(3);
            result = EPS_ERR_COMM_ERROR;
            QElapsedTimer wait; wait.start();
            while (wait.elapsed() < 120000) {
                if (!c->GetCurrentPrinterStatus(&status, &ink)) break;
                if (status.printerStatus == EPS_PRNST_IDLE && status.errorCode == EPS_PRNERR_NOERROR) {
                    result = EPS_ERR_NONE; break;
                }
                if (status.printerStatus == EPS_PRNST_ERROR) break;
                QThread::sleep(1);
            }
        }
    }
    close(lock);
    return result;
}
EPS_ERR_CODE EPSPrinterController::NozzleCheckPrinter() { return guardedMaintenance(false); }

''' + s[end:]
    start = s.index('EPS_ERR_CODE EPSPrinterController::HeadCleanPrinter()')
    end = s.index('EPS_INT32 EPSPrinterController::getSizeOfPrinterList()', start)
    s = s[:start] + 'EPS_ERR_CODE EPSPrinterController::HeadCleanPrinter() { return guardedMaintenance(true); }\n\n' + s[end:]
    s = replace(s, '#include <QThread>', '#include <QThread>\n#include <QElapsedTimer>\n#include <QMutex>\nstatic QMutex nativeSocketMutex(QMutex::Recursive);')
    for signature in [
        'static EPS_ERR_CODE guardedMaintenance(bool clean)',
        'void EPSPrinterController::StartFindPrinter()',
        'bool EPSPrinterController::ConnectToPrinter(const QString &printerName, const QString &printerId)',
        'bool EPSPrinterController::GetCurrentPrinterStatus(EPS_STATUS *status, EPS_INK_INFO* inkInfo)',
    ]:
        s = replace(s, signature + ' {', signature + ' {\n    QMutexLocker socketLock(&nativeSocketMutex);') if signature + ' {' in s else replace(s, signature + '\n{', signature + '\n{\n    QMutexLocker socketLock(&nativeSocketMutex);')
    return s
edit(U/'EPSCommonLib/EPSPrinterController.cpp', controller)

# Preserve device values. Missing color IDs must never become guessed colors.
def parser(s):
    start = s.index('#define EPS_INK_NORMALIZE_LEVEL')
    end = s.index('static ECB_PRINTER_STS ReadStatuslogfile', start)
    s = s[:start] + s[end:]
    s = replace(s, 'char lpReply[1024],', 'char lpReply[1025] = {0},')
    s = replace(s, '  sock_read (lpReply, &rep_len);', '  sock_read (lpReply, &rep_len);\n  lpReply[rep_len] = 0;')
    start = s.index('  }else{\n    char snink[3];')
    end = s.index('  /* Ink residual quantity analysis */', start)
    s = s[:start] + '  } // No INK field: leave the color list empty (unknown).\n\n' + s[end:]
    s = replace(s, "while (*lpInk != ';')", "while (*lpInk && *lpInk != ';' && strcspn(lpInk, \";\") >= 4)")
    s = replace(s, '   while (node)', '   while (node && ink_no < ECB_INK_NUM && lpInk[0] && lpInk[1] && lpInk[0] != \';\')')
    s = replace(s, '      node->rest = (int)strtol (ink, &stopstring, 16);',
                '      node->rest = (int)strtol (ink, &stopstring, 16);\n      if (stopstring != ink + 2) node->rest = -1;')
    s = replace(s, '\tshowInkInfo =  1; // 1: Show Ink Information', '')
    s = replace(s, '\tshowInkLow =  1;  // 1: Show Ink Low', '')
    s = replace(s, '    strncpy(WarningCode, lpSts + 3, 2);', '    strncpy(WarningCode, lpWR + 3, 2);')
    s = replace(s, '    return ECB_PRNST_IDLE;\n  }//if(lpWR)', '  }//if(lpWR)')
    s = replace(s, '  ink_num = 0;', '  ink_num = 0;\n  error_code = ECB_PRNERR_NOERROR;\n  showInkInfo = 0; showInkLow = 0;')
    s = replace(s, 'if(printer_status == ECB_DAEMON_NO_REPLY) return ECB_DAEMON_NO_REPLY;',
                'if(printer_status >= ECB_DAEMON_DOWN) return printer_status;')
    s = replace(s, '                status->inklevel[i] = serInkLevelNromalize( status->inklevel[i] );', '')
    # Drop the unused reset entry point from the built library.
    start = s.index('ECB_INK_RESET_STS Reset_Ink_Counter(')
    end = s.index('int Get_Printer_Info(', start)
    s = s[:start] + s[end:]
    s = replace(s, '    if (rsize == 0) return 0;', '    if (rsize <= 0 || rsize >= (int)sizeof(deviceid)) return 0;') if '    if (rsize == 0) return 0;' in s else s.replace('\tif (rsize == 0) return 0;', '\tif (rsize <= 0 || rsize >= (int)sizeof(deviceid)) return 0;')
    s = replace(s, '\tstrcpy (printer->manufacture, manufacture+4);', '\tif (!manufacture || !command || !model) return 0;\n\tstrcpy (printer->manufacture, manufacture+4);')
    return s
edit(U/'BackendLib/backend_api.c', parser)

# Native TCP framing, fixing short I/O, error propagation and descriptor leaks.
# Never replay a maintenance command after an uncertain write.
def transport(s):
    s = replace(s, '#include <unistd.h>', '#include <unistd.h>\n#include <sys/time.h>')
    s = replace(s, 'htonl (INADDR_ANY)', 'htonl (INADDR_LOOPBACK)')
    s = replace(s, '  server_sock_fd = sockfd;', '''  struct timeval timeout = {5, 0};
  setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
  setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
  server_sock_fd = sockfd;''')
    s = replace(s, '      shutdown (server_sock_fd, 2);', '      shutdown (server_sock_fd, 2);\n      close(server_sock_fd);')
    s = replace(s, 'packet[3] = size / 0xFF;', 'packet[3] = size / 0x100;')
    s = replace(s, 'packet[4] = size % 0xFF;', 'packet[4] = size % 0x100;')
    s = replace(s, '  if (size <= 0)\n    return 0;', '  if (size <= 0 || size > Max_Data_Size)\n    return -1;')
    start = s.index('  size = send (server_sock_fd,')
    end = s.index('\nint\nsock_reopen', start)
    s = s[:start] + '''  int total = size + Header_Size, sent = 0;
  while (sent < total) {
    int n = send(server_sock_fd, packet + sent, total - sent, MSG_NOSIGNAL);
    if (n <= 0) return -1;
    sent += n;
  }
  *lp_wsize = size;
  return 0;
}

int
sock_read (char* buf, int* lp_rsize)
{
  unsigned char header[Header_Size];
  int capacity = *lp_rsize;
  *lp_rsize = 0;
  if (server_sock_fd < 0) return -1;
  if (recv(server_sock_fd, header, Header_Size, MSG_WAITALL) != Header_Size) return -1;
  if (memcmp(header, Packet_Key, Key_Size) != 0) return -1;
  int size = (header[3] << 8) | header[4];
  if (size == 0) {
    unsigned char error;
    if (recv(server_sock_fd, &error, 1, MSG_WAITALL) != 1) return -1;
    return error;
  }
  if (size > capacity || size > Max_Data_Size) return -1;
  if (recv(server_sock_fd, buf, size, MSG_WAITALL) != size) return -1;
  *lp_rsize = size;
  return 0;
}
''' + s[end:]
    start = s.index('int\nsock_write_abandon_reply')
    s = s[:start] + '''int
sock_write_abandon_reply (char* buf, int* lp_wsize)
{
  char dummy[128]; int len = sizeof(dummy);
  if (sock_write(buf, lp_wsize) < 0) return 1;
  return sock_read(dummy, &len) != 0;
}
int
sock_write_with_reply (char* buf, int* lp_wsize, char* rbuf, int* lp_rsize)
{
  int len = 255; int tmp_size = *lp_wsize;
  *lp_rsize = 0;
  if (sock_write(buf, lp_wsize) < 0) {
    if (sock_reopen() < 0) return 1;
    *lp_wsize = tmp_size;
    if (sock_write(buf, lp_wsize) < 0) return 1;
  }
  if (sock_read(rbuf, &len) != 0) return 1;
  *lp_rsize = len;
  return 0;
}
'''
    return s
edit(U/'BackendLib/ekpcom.c', transport)

# The daemon stays in the foreground for Type=simple systemd supervision.
def daemon(s):
    start = s.index('\tif (geteuid () != 0)')
    end = s.index('\t/* start create ecbd.pid file */', start)
    s = s[:start] + s[end:]
    start = s.index('\t/* shift to daemon process */')
    end = s.index('\t/* write pid', start)
    s = s[:start] + '\t/* systemd supervises this foreground process. */\n' + s[end:]
    s = replace(s, '#define ECBD_VERSION', '#include "usb-selector.h"\n\n#define ECBD_VERSION')
    s = replace(s, '\tfor(i = 0; i < numdev; i++){', '''    int candidates = 0;
    for (i = 0; i < numdev; ++i) if (epson_usb_matches(pplist[i])) candidates++;
    if (candidates != 1) {
        if (candidates > 1) fprintf(stderr, "ecbd: ambiguous USB selection; configure EPSON_USB_SERIAL\\n");
        goto openLibusbFinish;
    }
\tfor(i = 0; i < numdev; i++){''')
    s = replace(s, '\t\tlibusb_device    *pdev = pplist[i];', '\t\tlibusb_device    *pdev = pplist[i];\n        if (!epson_usb_matches(pdev)) continue;')
    s = replace(s, 'mDevHandle = NULL;\n\t\t\t\t\t\t\tgoto', '*mDevHandle = NULL;\n\t\t\t\t\t\t\tgoto')
    return s
edit(B/'daemon/cbtd.c', daemon)
for path in [B/'daemon/cbtd.h', B/'daemon/epson-typdefs.h', B/'daemon/cbtd_datatrans.c']:
    edit(path, lambda s: s.replace('/var/run/ecbd.pid', '/run/epson-printer-utility/ecbd.pid').replace('/var/run/ecblp', '/run/epson-printer-utility/ecblp').replace('mkfifo (path, 0666)', 'mkfifo (path, 0660)'))

# Restrict the daemon's reachable command surface to the requested features.
def comserv(s):
    start = s.index('\t/* power ink flushing */', s.index('comserv_work (P_CBTD_INFO p_info'))
    end = s.index('\t/* get deviceid */', start)
    s = s[:start] + s[end:]
    start = s.index('\t/* set sleep timer */', s.index('comserv_work (P_CBTD_INFO p_info'))
    end = s.index('  \n\tif (err)', start)
    s = s[:start] + '\telse { return error_recept(fd, ERRPKT_UNKNOWN_PACKET); }\n' + s[end:]
    s = s.replace('char inputslot[2];', 'char inputslot[3] = {0};').replace('char mediatype[2];', 'char mediatype[3] = {0};').replace('char pagesize[2];', 'char pagesize[3] = {0};')
    s = replace(s, '\tSendCommand (buffer, bufsize);', '\tif (SendCommand (buffer, bufsize) != STS_NO_ERROR) return 1;')
    s = replace(s, 'htonl (INADDR_ANY)', 'htonl (INADDR_LOOPBACK)')
    s = replace(s, '\tbind (fd, (struct sockaddr *)&addr, sizeof (addr));', '')
    s = replace(s, '\tlisten (fd, 5);', '\tif (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0 || listen(fd, 5) < 0) { close(fd); return -1; }')
    # Refuse oversized packets before writing beyond the native command buffer.
    s = replace(s, '\tif (sock_read (fd, cbuf, *csize))', '\tif (*csize > COM_BUF_SIZE || *csize < 1) return 1;\n\tif (sock_read (fd, cbuf, *csize))')
    s = replace(s, '\tchar cbuf[COM_BUF_SIZE];', '\tchar cbuf[COM_BUF_SIZE] = {0};')
    return s
edit(B/'daemon/cbtd_comserv.c', comserv)

# Correct the C declarations required on 64-bit hosts (implicit malloc truncates pointers).
edit(B/'daemon/epmnt.c', lambda s: '#include <stdlib.h>\n#include <string.h>\n' + s)

# This is a standalone maintenance utility; remove obsolete lpd shell commands.
def remove_lpd(s):
    start = s.index('static void\nlpd_stop (P_CBTD_INFO p_info)\n{')
    end = s.index("typedef struct", start)
    return s[:start] + "static void lpd_stop(P_CBTD_INFO p_info) {}\nstatic void lpd_start(P_CBTD_INFO p_info) {}\n" + s[end:]
edit(B/'daemon/cbtd_datatrans.c', remove_lpd)

edit(U/'EPSCommonLib/escpr-lib/src/epson-usb.c', lambda s: re.sub(r'(EPS_FILEDSC\s+fd =) NULL;', r'\1 -1;', s))

# Repair an upstream preprocessor typo and avoid conflicting command-line definitions.
edit(U/'EPSCommonLib/escpr-lib/inc/epson-protocol.h', lambda s: re.sub(r'#define GCOMSW_PRT_USE_LPR\s+1\*/', '#ifndef GCOMSW_PRT_USE_LPR\n#define GCOMSW_PRT_USE_LPR 1\n#endif', s))

edit(U/'EPUCommon/EPUCommonDef.h', lambda s: replace(s, 'EPU_ERR_FAILURE         = 0x80000000', 'EPU_ERR_FAILURE         = (-2147483647 - 1)'))

edit(B/'daemon/cbtd_comserv.c', lambda s: s.replace('return post_prt_status (p_info);', 'return 1;'))

# The local utility sends the older nozzlecheck token, while 1.3.1 only dispatched
# nozzlecheck2. Route it to the same original command builder with plain ASF defaults.
def nozzle_compat(s):
    marker = '\t/* nozzle check 2 */'
    branch = '''    else if (csize == 11 && memcmp(cbuf, "nozzlecheck", 11) == 0) {
        if (nozzlecheck_recept(p_info, fd, "01", "00", "00")) err = 1;
    }

'''
    s = replace(s, marker, branch + marker)
    # Report FIFO write failure instead of silently acknowledging it.
    s = replace(s, 'if (wbytes < 0) {', 'if (wbytes <= 0) {\n            res = EPS_PRNERR_COMM;')
    return s
edit(B/'daemon/cbtd_comserv.c', nozzle_compat)

# The native GUI now saves into XDG_CONFIG_HOME as the current user.
edit(U/'PrinterUtility/EPUPrinterController.cpp', lambda s: re.sub(r'^.*system\("chown .*\n', '', s, flags=re.M))

# USB is connected through BackendLib/ecbd; epsSetPrinter configures native network.
def usb_connect(s):
    return replace(s, '        code = epsSetPrinter(&m_currentPrinter);', '''        if (i == prList.size()) return false;
        if (m_currentPrinter.protocol != EPS_PROTOCOL_USB)
            code = epsSetPrinter(&m_currentPrinter);''')
edit(U/'EPSCommonLib/EPSCommunicator.cpp', usb_connect)

# These two upstream CUPS headers are unused in the native maintenance path.
for path in [U/'EPSCommonLib/EPSCommunicator.cpp', U/'PrinterUtility/EPUPrinter.cpp']:
    edit(path, lambda s: s.replace('#include <cups/cups.h>\n', ''))
edit(U/'EPSCommonLib/EPSCommunicator.cpp', lambda s: '#include <unistd.h>\n' + s)
edit(U/'PrinterUtility/EPUMainController.cpp', lambda s: '#include <unistd.h>\n' + s)

# Shared model additions are local ABI extensions: all consumers are built together.
for path, marker in [(U/'BackendLib/backend_api.h', '} ECB_STATUS;'),
                     (U/'EPSCommonLib/escpr-lib/inc/epson-escpr-def.h', '} EPS_STATUS;')]:
    edit(path, lambda s, marker=marker: replace(s, marker, '    unsigned int warnings; /* five public warning bits, independent of faults */\n' + marker))
edit(U/'EPSCommonLib/escpr-lib/inc/epson-escpr-pvt.h', lambda s: replace(s, 'EPS_PAPER_COUNT paper_count;', 'EPS_PAPER_COUNT paper_count;\n    unsigned int warnings;'))

# USB parser: bounded fields, all ink entries (including unknown levels), independent
# warnings, and the original little-endian counters without upstream XOR arithmetic.
def usb_reports(s):
    s = '#include "native-count.h"\n' + s
    s = replace(s, 'static ECB_BOOL\t\tshowInkLow;', 'static ECB_BOOL\t\tshowInkLow;\nstatic unsigned int warnings;')
    s = replace(s, '  StsCode[2] = 0;', '  StsCode[2] = 0;\n  WarningCode[2] = 0;\n  warnings = 0;')
    s = replace(s, '  sock_read (lpReply, &rep_len);\n  lpReply[rep_len] = 0;', '  if (sock_read(lpReply, &rep_len) != 0 || rep_len < 0 || rep_len > 1024) return ECB_DAEMON_NO_REPLY;\n  lpReply[rep_len] = 0;')
    s = replace(s, '    while (*lpInk &&', '    while (ink_num < ECB_INK_NUM && *lpInk &&')
    s = replace(s, '      node->id = strtol(ic, (char **)NULL, 16);', '''      char *end = NULL;
      node->id = strtol(ic, &end, 16);
      if (end != ic + 6) node->id = 0;
      colors[ink_num] = inkbox_get_inkid(node->id);
      inklevel[ink_num++] = -1;''')
    s = replace(s, '   ink_num = ink_no;', '   /* Keep entries with no reported level as unavailable. */')
    s = replace(s, 'if(lpCS){', 'if(lpCS && strcspn(lpCS + 3, ";") >= 2){')
    s = replace(s, 'hextoi(lpCS[3]);', '(hextoi(lpCS[3]) == 1);')
    s = replace(s, 'hextoi(lpCS[4]);', '(hextoi(lpCS[4]) == 1);')
    s = replace(s, '  *errorCode = ECB_PRNERR_NOERROR;\n\n  /* Status analysis */', '''  *errorCode = ECB_PRNERR_NOERROR;
  lpWR = strstr(lpReply, "WR:");
  if (lpWR) {
      char *p = lpWR + 3;
      while (p[0] && p[0] != ';' && p[1] && p[1] != ';') {
          int code = hextoi(p[0]) * 16 + hextoi(p[1]);
          switch (code) {
          case 0x00: warnings |= 1u << 0; break;
          case 0x20: warnings |= 1u << 1; break;
          case 0x21: warnings |= 1u << 2; break;
          case 0x45: warnings |= 1u << 3; break;
          case 0xB0: warnings |= 1u << 4; break;
          }
          p += 2; if (*p == ',') ++p;
      }
  }

  /* Status analysis */''')
    start = s.index('  /* Warning status analysis */')
    end = s.index('#if DEBUG', start)
    s = s[:start] + s[end:]
    s = replace(s, 'if(lpSts){', 'if(lpSts && strcspn(lpSts + 3, ";") >= 2){')
    s = replace(s, 'if(lpErr){', 'if(lpErr && strcspn(lpErr + 3, ";") >= 2){')
    s = replace(s, '  status->errorCode = error_code;', '  status->errorCode = error_code;\n  status->warnings = warnings;')
    # Avoid stale ink status for real zero after a previous query.
    s = replace(s, '  connect_daemon();', '  memset(status, 0, sizeof(*status));\n  connect_daemon();')
    s = re.sub(r'(papercount\.\w+) =\s+\(hextoi\((lp\w+)\[3\]\).*?;', r'\1 = epson_count_hex(\2 + 3);', s)
    # Device-ID fields are unordered in IEEE 1284 IDs. Retain serial when present.
    start = s.index('\tchar *manufacture, *command, *model;')
    s = s[:start] + '''    const char *command = NULL;
    printer->manufacture[0] = printer->modelname[0] = printer->serial[0] = 0;
    for (char *field = strtok(deviceid, ";"); field; field = strtok(NULL, ";")) {
        const char *value = strchr(field, ':');
        if (!value) continue;
        ++value;
        if (!strncmp(field, "MFG:", 4) || !strncmp(field, "MANUFACTURER:", 13))
            snprintf(printer->manufacture, sizeof(printer->manufacture), "%s", value);
        if (!strncmp(field, "MDL:", 4) || !strncmp(field, "MODEL:", 6))
            snprintf(printer->modelname, sizeof(printer->modelname), "%s", value);
        if (!strncmp(field, "CMD:", 4)) command = value;
        if (!strncmp(field, "SN:", 3) || !strncmp(field, "SERN:", 5))
            snprintf(printer->serial, sizeof(printer->serial), "%s", value);
    }
    if (!printer->modelname[0] || !printer->manufacture[0]) return 0;
    printer->language = command && strstr(command, "ESCPAGE") ? 2 : 1;
    return rsize;
}
'''
    # Native converter also emits these distinct reported color IDs.
    s = replace(s, '\tcase 0xD010:', '''    case 0xC040: color = ECB_COLOR_LIGHTLIGHTBLACK; break;
    case 0x3110: color = ECB_COLOR_GRAY; break;
    case 0xE020: color = ECB_COLOR_GREEN; break;
\tcase 0xD010:''')
    return s
edit(U/'BackendLib/backend_api.c', usb_reports)
edit(U/'BackendLib/backend_api.h', lambda s: replace(s, '\tECB_INT32\tlanguage;', '\tECB_INT8 serial[ECB_NAME_BUFFSIZE];\n\tECB_INT32\tlanguage;'))

# Network still uses Epson's parser. Carry warnings without overwriting device errors.
def network_reports(s):
    s = '#include "native-count.h"\n' + s
    s = s.replace('EPS_BOOL\tshowInkInfo = TRUE;', 'EPS_BOOL\tshowInkInfo = FALSE;').replace('EPS_BOOL\tshowInkLow  = TRUE;', 'EPS_BOOL\tshowInkLow  = FALSE;')
    for i, name in enumerate(['PAPERLOW', 'MBOX_NEAREND', 'MAINT_REQUIRED', 'CHECK_NOZZLE', 'CUTTRASH_FULL']):
        s = replace(s, 'pstInfo->nError = EPS_PRNWARN_' + name + ';', 'pstInfo->warnings |= 1u << %d;' % i)
    s = re.sub(r'(pstInfo->paper_count\.\w+) = \(\(Parameter\[(\d+)\]\).*?;',
               lambda m: m[1] + ' = ParameterByte >= ' + str(int(m[2])+4) + ' ? epson_count_le((const unsigned char *)Parameter + ' + m[2] + ') : -1;', s)
    # Guard the native binary record walker and cartridge stride before copying.
    s = replace(s, '        memcpy(Parameter, Field+2, (EPS_INT8)ParameterByte );', '''        if (ParameterByte > sizeof(Parameter) || Field + 2 + ParameterByte > EndField)
            return EPS_ERR_COMM_ERROR;
        memcpy(Parameter, Field+2, ParameterByte);''')
    s = replace(s, '    while ( Field < EndField ) {', '    while ( Field + 2 <= EndField ) {')
    s = replace(s, '                Ink = Parameter;', '                if (ParameterByte < 4 || (unsigned char)Parameter[0] < 3) return EPS_ERR_COMM_ERROR;\n                Ink = Parameter;')
    # Binary ink record reports cartridge type explicitly; do not infer from ink count.
    s = replace(s, 'case 0x00:    pstInfo->nColorType[i] = EPS_COLOR_BLACK;        break;', '''case 0x00:    pstInfo->nColorType[i] = (unsigned char)Ink[1] == 0x0B ? EPS_COLOR_MATTEBLACK : EPS_COLOR_BLACK; break;''')
    s = replace(s, '                    switch( Ink[3] ) {', '                    switch( (unsigned char)Ink[3] ) {')
    return s
edit(U/'EPSCommonLib/escpr-lib/src/epson-escpr-services.c', network_reports)
edit(U/'EPSCommonLib/escpr-lib/src/epson-escpr-api.c', lambda s: replace(s, 'status->paper_count.color = stInfo.paper_count.color;', 'status->warnings = stInfo.warnings;\n\tstatus->paper_count.color = stInfo.paper_count.color;'))

# Optional USB initialization, native network probing, and reconnect/switch correctness.
def connections(s):
    s = replace(s, '\tret2 = Init_Lib();', '\tret2 = qgetenv("EPSON_CONNECTION") == "network" ? ECB_DAEMON_NO_ERROR : Init_Lib();')
    s = replace(s, '    return true;\n}\n\nEPS_ERR_CODE EPSCommunicator::NozzleCheckPrinter()', '    return retStatus == EPS_ERR_NONE;\n}\n\nEPS_ERR_CODE EPSCommunicator::NozzleCheckPrinter()')
    s = replace(s, '    internalRunFindPrinterLoop();', '    if (qgetenv("EPSON_CONNECTION") != "usb") internalRunFindPrinterLoop();')
    s = replace(s, 'int rsize = Get_Printer_Info(&printer_usb);', 'int rsize = qgetenv("EPSON_CONNECTION") == "network" ? 0 : Get_Printer_Info(&printer_usb);')
    s = replace(s, 'strcpy(printer.printerID , "USB");', '''snprintf(printer.printerID, sizeof(printer.printerID), "USB%s%s", printer_usb.serial[0] ? ":" : "", printer_usb.serial);
        snprintf(printer.serialNo, sizeof(printer.serialNo), "%s", printer_usb.serial);''')
    s = replace(s, 'sprintf(modelname_with_USB, "%s (USB)", printer_usb.modelname);', 'snprintf(modelname_with_USB, sizeof(modelname_with_USB), "%.56s (USB)", printer_usb.modelname);')
    # Validate selection on every call. A failed set must not make a later call succeed.
    start = s.index('    EPS_ERR_CODE code = EPS_ERR_NONE;', s.index('bool EPSCommunicator::ConnectToPrinter'))
    end = s.index('\nbool EPSCommunicator::GetPrinterStatus', start)
    s = s[:start] + '''    for (const EPS_PRINTER &p : m_printerList) {
        if (QString::fromLocal8Bit(p.printerID) != printerId || QString::fromLocal8Bit(p.modelName) != printerName) continue;
        if (QString::fromLocal8Bit(m_currentPrinter.printerID) == printerId) return true;
        if (p.protocol != EPS_PROTOCOL_USB && epsSetPrinter(&p) != EPS_ERR_NONE) return false;
        m_currentPrinter = p;
        return true;
    }
    return false;
}

''' + s[end:]
    s = replace(s, '    EPS_ERR_CODE retState = EPS_ERR_NONE;\n\tECB_PRINTER_STS', '''    memset(status, 0, sizeof(*status));
    memset(inkInfo, 0, sizeof(*inkInfo));
    status->printerStatus = -1;
    status->errorCode = EPS_PRNERR_COMM;
    memset(&status->paper_count, 0xff, sizeof(status->paper_count));
    if (!m_currentPrinter.printerID[0]) return false;
    EPS_ERR_CODE retState = EPS_ERR_NONE;
\tECB_PRINTER_STS''')
    # Status remains usable even if an independent ink query is unsupported.
    s = replace(s, 'retState = epsGetInkInfo(inkInfo);', 'if (epsGetInkInfo(inkInfo) != EPS_ERR_NONE) memset(inkInfo, 0, sizeof(*inkInfo));')
    s = replace(s, '        EThreadFree(m_pFindPrinterThread);', '        EThreadFree(m_pFindPrinterThread);')
    s = replace(s, 'EPSCommunicator::~EPSCommunicator()\n{', 'EPSCommunicator::~EPSCommunicator()\n{\n    Close_Lib();\n    epsReleaseDriver();')
    s = replace(s, 'retState = EPS_PRNERR_COMM;', 'retState = EPS_ERR_COMM_ERROR;')
    # Share a single native maintenance job builder for both existing network actions.
    for signature, cmd in [('NozzleCheckPrinter', 'EPS_MNT_NOZZLE'), ('HeadCleanPrinter', 'EPS_MNT_CLEANING')]:
        start = s.index('\t\tEPS_JOB_ATTRIB', s.index('EPS_ERR_CODE EPSCommunicator::'+signature))
        end = s.index('\n\t}\n\n    return retState;', start)
        s = s[:start] + '        return nativeNetworkMaintenance(' + cmd + ');' + s[end:]
    pos = s.index('EPS_ERR_CODE EPSCommunicator::NozzleCheckPrinter()')
    s = s[:pos] + '''static EPS_ERR_CODE nativeNetworkMaintenance(int command) {
    EPS_JOB_ATTRIB job = {}; job.version = EPS_JOB_ATTRIB_VER_CUR;
    job.colorPlane = EPS_CP_PRINTCMD; job.cmdType = command;
    EPS_ERR_CODE ret = epsStartJob(&job);
    if (ret != EPS_ERR_NONE) return ret;
    EPS_UINT32 size = 0;
    ret = epsMakeMainteCmd(command, NULL, &size);
    EPS_UINT8 *buffer = ret == EPS_ERR_NONE ? (EPS_UINT8 *)malloc(size) : NULL;
    if (!buffer) { epsCancelJob(0); return EPS_ERR_MEMORY_ALLOCATION; }
    ret = epsMakeMainteCmd(command, buffer, &size);
    EPS_PRN_DATA data = {}; data.version = EPS_PRN_DATA_VER_CUR; data.chunk.version = EPS_PRN_DATA_VER_CUR;
    EPS_UINT32 offset = 0;
    while (ret == EPS_ERR_NONE && offset < size) {
        data.chunk.data = buffer + offset; data.chunk.dataSize = size - offset;
        ret = epsSendData(&data);
        if (ret == EPS_ERR_NONE && !data.chunk.dataSize) ret = EPS_ERR_COMM_ERROR;
        offset += data.chunk.dataSize;
    }
    free(buffer);
    if (ret != EPS_ERR_NONE) { epsCancelJob(0); return ret; }
    return epsEndJob();
}

''' + s[pos:]
    return s
edit(U/'EPSCommonLib/EPSCommunicator.cpp', connections)

# Serialise every entry using the same native driver, including list getters.
def controller_model(s):
    for signature in ['QVector<EPS_PRINTER> EPSPrinterController::GetPrinterList()', 'EPS_INT32 EPSPrinterController::getSizeOfPrinterList()']:
        s = replace(s, signature + '\n{', signature + '\n{\n    QMutexLocker socketLock(&nativeSocketMutex);')
    s += '''
EPS_ERR_CODE EPSPrinterController::MaintainPrinter(const QString &name, const QString &id, bool clean) {
    QMutexLocker socketLock(&nativeSocketMutex);
    if (!ConnectToPrinter(name, id)) return EPS_ERR_COMM_ERROR;
    return guardedMaintenance(clean);
}
'''
    return s
edit(U/'EPSCommonLib/EPSPrinterController.cpp', controller_model)
edit(U/'EPSCommonLib/EPSPrinterController.h', lambda s: replace(s, '    EPS_ERR_CODE HeadCleanPrinter();', '    EPS_ERR_CODE HeadCleanPrinter();\n    EPS_ERR_CODE MaintainPrinter(const QString &name, const QString &id, bool clean);'))

# Keep Epson's GUI, using exactly the shared ink validity and counter interpretation.
def gui_model(s):
    s = '#include "native-report.h"\n' + s
    start = s.index('void EPUMainView::updatePrinterInkInfo()')
    end = s.index('\nvoid EPUMainView::', start + 10)
    s = s[:start] + '''void EPUMainView::updatePrinterInkInfo() {
    for (auto *view : m_inkLevelViewArray) { m_pInkBox->removeWidget(view); delete view; }
    m_inkLevelViewArray.clear();
    EPUPrinter *printer = EPUPrinterController::GetInstance()->GetCurrentPrinter();
    EPS_INK_INFO info = {};
    if (printer && !printer->GetPrinterDisconnected()) info = printer->GetInkInfo();
    const int n = qBound(0, info.number, EPS_INK_NUM);
    for (int i = 0; i < qMax(1, n); ++i) {
        const bool known = i < n && epson::inkAvailable(info, i);
        const QString name = i < n ? QString::fromLatin1(epson::colorName(info.colors[i])) : tr("Unknown");
        auto *view = new EPUInkLevelView(i < n ? eprpColorToQColor(info.colors[i]) : QColor(Qt::gray), name);
        view->SetInkLevel(known ? info.remaining[i] : -1);
        view->setToolTip(i < n ? QString("Color ID %1; raw %2; ink status %3").arg(info.colors[i]).arg(info.remaining[i]).arg(info.status[i]) : tr("No color IDs reported"));
        view->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        view->setFixedHeight(180);
        m_inkLevelViewArray.push_back(view); m_pInkBox->addWidget(view);
    }
}
''' + s[end:]
    start = s.index('void EPUMainView::updateCurrenInkJetPrinterStaus()')
    end = s.index('void EPUMainView::updateCurrenPrinterStaus()', start)
    s = s[:start] + '''void EPUMainView::updateCurrenInkJetPrinterStaus() {
    EPUPrinter *p = EPUPrinterController::GetInstance()->GetCurrentPrinter();
    if (!p) return;
    const EPS_STATUS status = p->GetPrinterStatus();
    const EPS_INK_INFO ink = p->GetInkInfo();
    PrinterLogoNormal();
    updatePrinterState(status.printerStatus, status.errorCode);
    const qint64 count = epson::fedTotal(status.paper_count);
    m_pPaperCountLabel->setText(count < 0 ? tr("Number of sheets of paper fed: unavailable") : tr("Number of sheets of paper fed: %1").arg(count));
    m_pPaperCountLabel->setToolTip(tr("Native feed counters; not a count of successfully printed pages."));
    bool low = false;
    for (int i = 0; i < qBound(0, ink.number, EPS_INK_NUM); ++i)
        low |= epson::inkAvailable(ink, i) && ink.showInkLow && ink.remaining[i] > 0 && ink.remaining[i] <= INKLOW;
    if (status.errorCode != EPS_PRNERR_NOERROR) {
        PrinterLogoError();
        // Include a stable detail even for native network conditions without a translation.
        setPrinterStatus(QString::fromLatin1(epson::errorName(status.errorCode)));
    } else if (status.warnings || low) {
        PrinterLogoWarning();
        QStringList labels;
        for (const auto &v : epson::warnings(status.warnings)) labels.append(v.toString());
        if (low) labels.append(tr("Ink Low"));
        setPrinterStatus(labels.join(", "));
    }
    if (m_pDelegate) {
        if (status.printerStatus != EPS_PRNST_IDLE || status.errorCode != EPS_PRNERR_NOERROR)
            m_pDelegate->EPUViewDisAble();
        else { m_pDelegate->EPUViewEnAble(); if (low) m_pDelegate->EPUViewDisAbleHeadClean(); }
    }
}

''' + s[end:]
    # Even the no-device default must not display guessed empty ink cartridges.
    start = s.index('/*\n    //set default ink')
    end = s.index('    inkTempLayout->addSpacing(20);',start)
    s = s[:start] + s[end:]
    s = s.replace('int level = 0;', 'int level = -1;')
    return s
edit(U/'PrinterUtility/EPUMainView.cpp', gui_model)
edit(U/'PrinterUtility/EPUPrinter.cpp', lambda s: replace(s, '    m_status.errorCode = status.errorCode;', '    m_status = status;'))
def gui_no_guess(s):
    s = s.replace('EPS_INK_INFO ink;', 'EPS_INK_INFO ink = {};').replace('EPS_STATUS status;', 'EPS_STATUS status = {};')
    start = s.index('\t\t\tif(!ret)')
    end = s.index('            /*if(ret)', start)
    s = s[:start] + '''            if (!ret) {
                inkInfo = {}; status = {};
                status.printerStatus = -1; status.errorCode = EPS_PRNERR_COMM;
                memset(&status.paper_count, 0xff, sizeof(status.paper_count));
            }
''' + s[end:]
    return s
edit(U/'PrinterUtility/EPUPrinterController.cpp', gui_no_guess)
def ink_paint(s):
    s = replace(s, '\tint Draw_Inklevel=m_nInkLevel;', '''    if (m_nInkLevel < 0 || m_nInkLevel > 100) {
        painter.drawText(rect(), Qt::AlignCenter, m_strInkName + "\\n" + tr("Unknown"));
        return;
    }
\tint Draw_Inklevel=m_nInkLevel;''')
    s = replace(s, '\t\tif(m_nInkLevel <= 3) Draw_Inklevel = 3;', '')
    s = replace(s, 'QString inkLevelText = QString::number(Draw_Inklevel);', 'QString inkLevelText = QString::number(Draw_Inklevel) + "%";')
    s = replace(s, '//            painter.drawText', '              painter.drawText')
    return s
edit(U/'PrinterUtility/EPUInkLevelView.cpp', ink_paint)
# Native IDs are useful in the GUI as well, without assuming every ID ends in a MAC.
def gui_ids(s):
    start = s.index('\tQString PrinterID = printer->GetPrinterId();')
    end = s.index('    if(printer->GetPrintCmd()', start)
    return s[:start] + '    item->setData(printer->GetPrinterName() + " (" + printer->GetPrinterId() + ")", Qt::DisplayRole);\n' + s[end:]
edit(U/'PrinterUtility/EPUPrinterListDialog.cpp', gui_ids)

# Native maintenance runs in a worker. The existing view remains responsive; a
# second click, printer change or closing the view cannot destroy the live driver.
def gui_async(s):
    s = '#include <QtConcurrent/QtConcurrentRun>\n#include <QFutureWatcher>\n' + s
    s = replace(s, '    , m_nMaintenanceCommand(EPU_MAINTENANCE_COMMAND_NONE)', '    , m_nMaintenanceCommand(EPU_MAINTENANCE_COMMAND_NONE)\n    , m_operation(NULL)')
    start = s.index('void EPUMaintenanceGuideView::btnPrintClicked()')
    s = s[:start] + '''EPUMaintenanceGuideView::~EPUMaintenanceGuideView() {
    if (m_operation) m_operation->waitForFinished();
}

void EPUMaintenanceGuideView::btnPrintClicked() {
    if (m_operation) return;
    EPUPrinter *printer = EPUPrinterController::GetInstance()->GetCurrentPrinter();
    if (!printer) return;
    const QString name = printer->GetModelName(), id = printer->GetPrinterId();
    const bool clean = m_nMaintenanceCommand == EPU_MAINTENANCE_COMMAND_HEAD_CLEANING;
    if (!clean && m_nMaintenanceCommand != EPU_MAINTENANCE_COMMAND_NOZZLE_CHECK) return;
    m_pPrintButton->setEnabled(false); m_pCancelButton->setEnabled(false);
    if (m_pDelegate) m_pDelegate->EPUViewDisAble();
    m_pMaintenanceGuideLabel->setText(tr("Waiting for one maintenance operation. Do not resend it."));
    m_operation = new QFutureWatcher<int>(this);
    connect(m_operation, &QFutureWatcher<int>::finished, this, [this]() {
        const int result = m_operation->result();
        m_operation->deleteLater(); m_operation = NULL;
        m_pCancelButton->setEnabled(true);
        // Leave Print disabled until the guide is opened again; never invite a retry.
        m_pMaintenanceGuideLabel->setText(result == EPS_ERR_NONE ?
            tr("One operation submitted. Confirm the physical result at the printer.") :
            result == EPS_ERR_PRINTER_NOT_USEFUL ? tr("Skipped: printer busy, unavailable, or maintenance lock in use.") :
            tr("Operation unconfirmed. Check the printer before issuing any further command."));
    });
    m_operation->setFuture(QtConcurrent::run([name, id, clean]() {
        return int(EPSPrinterController::GetInstance()->MaintainPrinter(name, id, clean));
    }));
}
'''
    s = replace(s, '    m_nMaintenanceCommand = command;', '    m_nMaintenanceCommand = command;\n    m_pPrintButton->setEnabled(true); m_pCancelButton->setEnabled(true);')
    return s
edit(U/'PrinterUtility/EPUMaintenanceGuideView.cpp', gui_async)
edit(U/'PrinterUtility/EPUMaintenanceGuideView.h', lambda s: replace(replace(s, '#include "EPUOperationView.h"', '#include "EPUOperationView.h"\n#include <QFutureWatcher>'), '    void setupConnection();', '    QFutureWatcher<int> *m_operation;\n    void setupConnection();').replace('    explicit EPUMaintenanceGuideView(QWidget *parent = 0);', '    explicit EPUMaintenanceGuideView(QWidget *parent = 0);\n    ~EPUMaintenanceGuideView();'))

# One stable FIFO inode and matching paths/permissions for CUPS and the daemon.
edit(B/'src/backend.c', lambda s: s.replace('/var/run/ecblp', '/run/epson-printer-utility/ecblp'))
def fifo_stable(s):
    start = s.index('\tif (access (path, F_OK) == 0)', s.index('fifo_open (P_CBTD_INFO p_info'))
    end = s.index('\n\tif (is_sysflags', start)
    return s[:start] + '''    struct stat st;
    old_mask = umask(0007);
    int created = mkfifo(path, 0660);
    umask(old_mask);
    if (created < 0 && errno != EEXIST) return -1;
    if (lstat(path, &st) < 0 || !S_ISFIFO(st.st_mode)) return -1;
''' + s[end:]
edit(B/'daemon/cbtd_datatrans.c', fifo_stable)

# Preserve printing control (cancel/reset and specific resume queries), but keep
# generic command forwarding and unrelated maintenance out of the local API.
def print_coexist(s):
    s = '#include "backend-io.h"\n' + s
    s = replace(s, '\telse { return error_recept(fd, ERRPKT_UNKNOWN_PACKET); }', '''    else if (csize == 5 &&
        ((!memcmp(cbuf, "di\\x01\\x00\\x01", 5)) || (!memcmp(cbuf, "pe\\x01\\x00\\x01", 5)))) {
        if (default_recept(p_info, fd, cbuf, csize)) err = 1;
    }
    else { return error_recept(fd, ERRPKT_UNKNOWN_PACKET); }''')
    s = replace(s, '*csize = ((int)cbuf[3] << 8) + (int)cbuf[4];', '*csize = ((unsigned char)cbuf[3] << 8) | (unsigned char)cbuf[4];')
    s = replace(s, 'memcmp (cbuf, nozzlecheck2_command, sizeof (nozzlecheck2_command)) == 0', 'csize == 18 && memcmp (cbuf, nozzlecheck2_command, sizeof (nozzlecheck2_command)) == 0')
    # cached status is still a report of busy while the daemon drains a print job.
    s = replace(s, '\treply_send (fd, p_info->prt_status, p_info->prt_status_len);', '''    char status[PRT_STATUS_MAX];
    int size = p_info->prt_status_len;
    if (size <= 0 || size >= PRT_STATUS_MAX) return 1;
    memcpy(status, p_info->prt_status, size); status[size] = 0;
    char *state = strstr(status, "ST:");
    if (state && is_sysflags(p_info, ST_JOB_PRINTING) && !strncmp(state + 3, "04", 2)) memcpy(state + 3, "03", 2);
    reply_send(fd, status, size);''')
    # No recursive retries or reads outside the native reply buffer.
    s = replace(s, 'if (rbuf[7] == \'2\')', 'if (rsize > 7 && rbuf[7] == \'2\')')
    s = replace(s, '\t\t\tmemcpy (p_info->prt_status, rbuf, rsize);', '\t\t\tif (rsize >= PRT_STATUS_MAX) return 1;\n            memset(p_info->prt_status, 0, PRT_STATUS_MAX);\n\t\t\tmemcpy (p_info->prt_status, rbuf, rsize);')
    s = replace(s, '\t\tassert (read_possible_size >= read_size);', '\t\tif (read_size > read_possible_size || read_size > REP_BUF_SIZE) { leave_critical(p_info->ecbt_accsess_critical); return 1; }') if '\t\tassert (read_possible_size >= read_size);' in s else replace(s, '\t\t\tassert (read_possible_size >= read_size);', '\t\t\tif (read_size > read_possible_size || read_size > REP_BUF_SIZE) { leave_critical(p_info->ecbt_accsess_critical); return 1; }')
    s = replace(s, 'is_sysflags (p_info, ST_JOB_PRINTING) && (point[2] == 4)', 'point && is_sysflags (p_info, ST_JOB_PRINTING) && (point[2] == 4)')
    s = replace(s, 'n = point[1] / nparam;', 'if (nparam < 3) return 0;\n                n = (point[1] - 1) / nparam;')
    # Carry the actual black color code; never choose photo black by ink count.
    s = replace(s, '''}else if ( 6 <= n ){
						/* printer has 6 color ink or more. */
						strncpy(key, "A140", 4);''', '}else if (0) { /* Never infer photo black from cartridge count. */\n                        strncpy(key, "A140", 4);')
    # Preserve every native warning in WR, not only ink-low / maintenance-box hints.
    marker = '\t/* Maintenance Box Warning Codes */'
    s = replace(s, marker, '''    point = scan_bin_status(STBIN_WR, bdata, bsize);
    if (point && count + 4 + 2 * point[1] < csize) {
        count += sprintf(cdata + count, "WR:");
        for (int i = 0; i < point[1]; ++i) count += sprintf(cdata + count, "%02X", point[2+i]);
        count += sprintf(cdata + count, ";");
    }

''' + marker)
    s = replace(s, 'while (count < bsize) {', 'while (count + 2 <= bsize) {\n        if (count + 2 + bdata[count + 1] > bsize) return NULL;')
    s = replace(s, 'if (!bdata || memcmp(bdata, bheader, sizeof(bheader)))', 'if (!bdata || bsize < sizeof(bheader) || memcmp(bdata, bheader, sizeof(bheader)))')
    # FIFO operations never interleave writers or wait indefinitely for a reader.
    start = s.index('int SendCommand(char* pCmd, int nCmdSize)')
    s = s[:start] + '''int SendCommand(char* pCmd, int nCmdSize) {
    int lock = epson_fifo_lock(0);
    if (lock < 0) return EPS_PRNERR_COMM;
    int fd = epson_fifo_open(FIFO_PATH);
    int result = fd < 0 ? -1 : epson_fifo_write(fd, pCmd, nCmdSize);
    if (fd >= 0) close(fd);
    close(lock);
    return result == 0 ? STS_NO_ERROR : EPS_PRNERR_COMM;
}
'''
    return s
edit(B/'daemon/cbtd_comserv.c', print_coexist)
# Large status reports must fit through the original framing end to end.
edit(B/'daemon/cbtd.h', lambda s: replace(s, '#define PRT_STATUS_MAX 256', '#define PRT_STATUS_MAX 1024'))
edit(B/'daemon/cbtd_comserv.c', lambda s: replace(s, '#define REP_BUF_SIZE  256', '#define REP_BUF_SIZE  1024'))

def cups_backend(s):
    s = '#include "backend-io.h"\n' + s
    s = replace(s, '#include <cups/http.h>', '') # unused upstream header, no CUPS API calls
    start = s.index('\tdo\n\t{\n\t\tif ((fd = open')
    end = s.index('\n\t/*\n\t * Finally', start)
    s = s[:start] + '''    int operation = epson_operation_lock(1);
    if (operation < 0) return 1;
    int writer = epson_fifo_lock(1);
    if (writer < 0) { close(operation); return 1; }
    fd = -1;
    for (int attempt = 0; attempt < 50 && fd < 0; ++attempt) {
        fd = epson_fifo_open(resource);
        if (fd < 0 && errno != ENXIO && errno != ENOENT) break;
        if (fd < 0) usleep(100000);
    }
    if (fd < 0) {
        fprintf(stderr, "ERROR: ecbd FIFO unavailable\\n");
        close(writer); close(operation); return 1;
    }
''' + s[end:]
    start = s.index('\t\t\twhile (nbytes > 0)')
    end = s.index('\n\t\t\tif (argc > 6)', start)
    s = s[:start] + '''            if (epson_fifo_write(fd, bufptr, nbytes) < 0) {
                fprintf(stderr, "ERROR: print transfer failed; not replaying data\\n");
                close(fd); close(writer); close(operation); return 1;
            }
''' + s[end:]
    s = replace(s, '\tclose(fd);', '\tclose(fd);\n    close(writer); close(operation);')
    s = replace(s, '\treturn (0);', '\treturn ferror(fp) ? 1 : 0;')
    # ferror must be checked before fclose.
    s = replace(s, '\tif (fp != stdin)\n\t\tfclose(fp);\n\n\treturn ferror(fp) ? 1 : 0;', '\tint failed = ferror(fp);\n    if (fp != stdin) fclose(fp);\n    return failed ? 1 : 0;')
    # This backend manages one explicitly selected ecbd USB printer.
    start = s.index('\tfor (i = 0;;i ++)')
    end = s.index('\n\treturn;', start)
    s = s[:start] + '''    struct stat st;
    if (lstat(FIFO_PATH, &st) == 0 && S_ISFIFO(st.st_mode) && access(FIFO_PATH, W_OK) == 0)
        printf("direct ecblp:%s \\"Epson Backend\\" \\"Epson USB Printer (ecbd)\\"\\n", FIFO_PATH);
'''.replace('\\"', '\\"') + s[end:]
    return s
edit(B/'src/backend.c', cups_backend)

edit(B/'daemon/epson-typdefs.h', lambda s: replace(s, '"/run/epson-printer-utility/ecblp0"', 'EPSON_RUNTIME "/ecblp0"').replace('#define DAEMON_PORT', '#include "operation-lock.h"\n#define DAEMON_PORT'))

edit(B/'daemon/cbtd_comserv.c', lambda s: replace(s, '}else if (0) { /* Never infer photo black from cartridge count. */\n                        strncpy(key, "A140", 4);\n\t\t\t\t\t} else {', '} else {'))

# Retain reported IDs as well as Epson's shared color enum, including unknown
# colors. CI is an internal text-status field, not a new printer command.
for path, marker in [(U/'BackendLib/backend_api.h', '} ECB_STATUS;'),
                     (U/'EPSCommonLib/escpr-lib/inc/epson-escpr-def.h', '} EPS_INK_INFO;')]:
    edit(path, lambda s, marker=marker: replace(s, marker, '    int reportedColorIds[20];\n    int colorIdFormat; /* 0 unknown, 1 INK identifier, 2 ST2 cartridge type/color */\n' + marker))
edit(U/'EPSCommonLib/escpr-lib/inc/epson-escpr-pvt.h', lambda s: replace(s, '    unsigned int warnings;', '    unsigned int warnings;\n    int reportedColorIds[20];\n    int colorIdFormat;'))
def usb_color_ids(s):
    s = replace(s, 'static unsigned int warnings;', 'static unsigned int warnings;\nstatic int reportedColorIds[20], colorIdFormat;')
    s = replace(s, '  warnings = 0;', '  warnings = 0; colorIdFormat = 1;')
    s = replace(s, '      colors[ink_num] = inkbox_get_inkid(node->id);', '      reportedColorIds[ink_num] = node->id;\n      colors[ink_num] = inkbox_get_inkid(node->id);')
    s = replace(s, '  /* Ink residual quantity analysis */', '''  char *ci = strstr(lpReply, "CI:");
  if (ci) {
      ci += 3; colorIdFormat = 2;
      for (int i = 0; i < ink_num; ++i) {
          if (strcspn(ci, ";") < 4) { reportedColorIds[i] = -1; continue; }
          char id[5] = {0}; memcpy(id, ci, 4);
          char *end = NULL; long value = strtol(id, &end, 16);
          reportedColorIds[i] = end == id + 4 ? value : -1;
          ci += 4;
      }
  }

  /* Ink residual quantity analysis */''')
    s = replace(s, '  status->ink_num = ink_num;', '  status->ink_num = ink_num;\n  status->colorIdFormat = colorIdFormat;\n  memcpy(status->reportedColorIds, reportedColorIds, sizeof(reportedColorIds));')
    return s
edit(U/'BackendLib/backend_api.c', usb_color_ids)
edit(U/'EPSCommonLib/EPSCommunicator.cpp', lambda s: replace(s, 'inkInfo->number = qBound', 'inkInfo->colorIdFormat = status_usb.colorIdFormat;\n            memcpy(inkInfo->reportedColorIds, status_usb.reportedColorIds, sizeof(inkInfo->reportedColorIds));\n            inkInfo->number = qBound'))
def network_color_ids(s):
    s = replace(s, '                    pstInfo->nInkNo++;', '''                    pstInfo->reportedColorIds[i] = ((unsigned char)Ink[1] << 8) | (unsigned char)Ink[2];
                    pstInfo->colorIdFormat = 2;
                    pstInfo->nInkNo++;''')
    # Do not replace distinct device levels with the minimum of a combined cartridge.
    start = s.index('\tif(InkCartridgeType == MI_CARTRIDGE_ONE) {')
    end = s.index('\n\tpstInfo->showInkLow', start)
    return s[:start] + s[end:]
edit(U/'EPSCommonLib/escpr-lib/src/epson-escpr-services.c', network_color_ids)
edit(U/'EPSCommonLib/escpr-lib/src/epson-protocol.c', lambda s: replace(s, '\t\tinfo->number         = lclStatus.nInkNo;', '\t\tinfo->colorIdFormat = lclStatus.colorIdFormat;\n        memcpy(info->reportedColorIds, lclStatus.reportedColorIds, sizeof(info->reportedColorIds));\n\t\tinfo->number         = lclStatus.nInkNo;'))
def daemon_color_ids(s):
    marker = '\t/* Printing Count */'
    s = replace(s, marker, '''    point = scan_bin_status(STBIN_IC, bdata, bsize);
    if (point && point[1] && point[2] >= 3) {
        int stride = point[2], n = (point[1] - 1) / stride;
        if (count + 4 + 4 * n < csize) {
            count += sprintf(cdata + count, "CI:");
            for (int i = 0; i < n; ++i) count += sprintf(cdata + count, "%02X%02X", point[3+i*stride], point[4+i*stride]);
            count += sprintf(cdata + count, ";");
        }
    }

''' + marker)
    return s
edit(B/'daemon/cbtd_comserv.c', daemon_color_ids)

# A disappearing FIFO/network reader is an I/O failure, never a fatal SIGPIPE.
edit(B/'daemon/cbtd_signal.c', lambda s: replace(s, '  signal (SIGHUP, kill_cbtd);', '  signal(SIGPIPE, SIG_IGN);\n  signal (SIGHUP, kill_cbtd);'))
edit(B/'src/backend.c', lambda s: replace(s, '\tsetbuf (stderr, NULL);', '\tsignal(SIGPIPE, SIG_IGN);\n\tsetbuf (stderr, NULL);'))
edit(U/'EPSCommonLib/epsmp/linux/linux_net.c', lambda s: replace(s, 'send((EPS_SOCKET)sockfd, msg, len, 0)', 'send((EPS_SOCKET)sockfd, msg, len, MSG_NOSIGNAL)'))
edit(U/'BackendLib/backend_api.c', lambda s: replace(s, 'return ECB_DAEMON_PRINTER_RESET;', 'return ECB_PRNST_CANCELLING;'))


# Annotate the final adapted files, once per file, without changing the retained
# archives or replacing any upstream copyright/license/exception notice.
modification_notice = f"""/*
 * Modified by the epson-printer-utility-nix project.
 * Modification date: {MODIFICATION_DATE}.
 * Local adaptation details: patches/adapt.py and CHANGELOG.md.
 * Original copyright, license and exception notices below remain in effect.
 */
"""
modified_files = []
for path, original in sorted(original_files.items()):
    if path.read_bytes() != original:
        assert path.suffix in ('.c', '.cpp', '.h'), path
        path.write_text(modification_notice + path.read_text())
        modified_files.append(str(path))
Path('UPSTREAM-MODIFICATIONS.txt').write_text(
    f"epson-printer-utility-nix upstream adaptations dated {MODIFICATION_DATE}\n"
    "Original source archives remain unchanged. Each file below carries a\n"
    "modification notice; its original licensing notices remain in effect.\n\n"
    + ''.join(name + '\n' for name in modified_files))
