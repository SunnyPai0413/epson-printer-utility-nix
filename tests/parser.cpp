// Feed fixture status strings into Epson's own parser; never represents a live printer.
#include <cstring>
#include <cstdlib>
#include "BackendLib/backend_api.h"
#include "BackendLib/ekpcom.h"
static const char *reply;
int sock_open() { return 0; }
void sock_close() {}
int sock_reopen() { return -1; }
int sock_write(char *, int *) { return 0; }
int sock_read(char *buf, int *size) {
    if (!reply) { *size = 0; return -1; }
    *size = strlen(reply); memcpy(buf, reply, *size); return 0;
}
int sock_write_abandon_reply(char *, int *) { std::abort(); }
int sock_write_with_reply(char *, int *, char *, int *) { std::abort(); }
static void require(bool v) { if (!v) std::abort(); }
int main() {
    ECB_STATUS status = {};
    reply = "ST:04;CS:11;IQ:0C0001643269;INK:732062105408430432021101;";
    require(Get_Status(&status) == ECB_DAEMON_NO_ERROR);
    require(status.printerStatus == ECB_PRNST_IDLE && status.ink_num == 6);
    require(status.colors[0] == 5 && status.inklevel[0] == 12); // no 5% rounding
    require(status.colors[1] == 4 && status.inklevel[1] == 0); // true zero retained
    require(status.colors[5] == 0 && status.inkstatus[5] < 0); // unavailable marker
    reply = "ST:01;WR:FF;CS:11;IQ:64;INK:1101;";
    require(Get_Status(&status) == ECB_DAEMON_NO_ERROR && status.printerStatus == ECB_PRNST_BUSY);
    reply = "ST:00;ER:06;"; // error/status remains readable with no ink fields
    require(Get_Status(&status) == ECB_DAEMON_NO_ERROR);
    require(status.errorCode == ECB_PRNERR_PAPEROUT && status.ink_num == 0);
    reply = "ST:04;CS:11;AI:CW:06;IQ:646464646464;";
    require(Get_Status(&status) == ECB_DAEMON_NO_ERROR && status.ink_num == 0); // never infer slot colors
}
