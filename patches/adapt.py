#!/usr/bin/env python3
"""Small, asserted edits to the local 1.1.3/1.3.1 sources; never downloads code."""
from pathlib import Path
import re
U = Path('epson-printer-utility')
B = Path('epson-backend')
def edit(path, fn):
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

# USB-only discovery: no network probing, no alternative protocol implementation.
def communicator(s):
    s = replace(s, '    internalRunFindPrinterLoop();', '    // USB discovery uses the original backend API below.')
    s = replace(s, '\t \tprintf (\"Communication daemon down, Error code = %d\\n\", ret2 );', '\t \tqWarning(\"ecbd unavailable; start ecbd.service\");')
    s = replace(s, '\t\texit(1);', '\t\t// Keep the GUI usable when ecbd is offline.')
    s = replace(s, 'ECB_STATUS status_usb;', 'ECB_STATUS status_usb = {};')
    s = replace(s, 'status->printerStatus = status_usb.printerStatus;', '''switch (status_usb.printerStatus) {
            case ECB_PRNST_IDLE: status->printerStatus = EPS_PRNST_IDLE; break;
            case ECB_PRNST_BUSY: status->printerStatus = EPS_PRNST_BUSY; break;
            case ECB_PRNST_PRINTING: status->printerStatus = EPS_PRNST_PRINTING; break;
            case ECB_PRNST_CANCELLING: status->printerStatus = EPS_PRNST_CANCELLING; break;
            default: status->printerStatus = EPS_PRNST_ERROR; break;
            }''')
    s = replace(s, 'status->errorCode = status_usb.errorCode;', '''switch (status_usb.errorCode) {
            case ECB_PRNERR_NOERROR: status->errorCode = EPS_PRNERR_NOERROR; break;
            case ECB_PRNERR_PAPEROUT: status->errorCode = EPS_PRNERR_PAPEROUT; break;
            case ECB_PRNERR_PAPERJAM: status->errorCode = EPS_PRNERR_PAPERJAM; break;
            case ECB_PRNERR_INKOUT: status->errorCode = EPS_PRNERR_INKOUT; break;
            case ECB_PRNERR_COVEROPEN: status->errorCode = EPS_PRNERR_COVEROPEN; break;
            default: status->errorCode = EPS_PRNERR_GENERAL; break;
            }''')
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
    s = replace(s, '  ink_num = 0;', '  ink_num = 0;\n  error_code = ECB_PRNERR_GENERAL;\n  showInkInfo = 0; showInkLow = 0;')
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
    start = s.index('\t/* stop printing (not D4) */', s.index('comserv_work (P_CBTD_INFO p_info'))
    end = s.index('\t/* nozzle check 2 */', start)
    s = s[:start] + s[end:]
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

# USB is already connected through BackendLib/ecbd. epsSetPrinter only configures
# escpr-lib's network/legacy USB transport, which is intentionally unused here.
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
