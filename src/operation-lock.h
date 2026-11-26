/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef EPSON_OPERATION_LOCK_H
#define EPSON_OPERATION_LOCK_H
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>
#define EPSON_RUNTIME "/run/epson-printer-utility"
#define EPSON_LOCK EPSON_RUNTIME "/operation.lock"
/* Created by the module's tmpfiles rule, shared by the GUI and CLI. Never unlink it. */
static inline int epson_operation_lock(int wait) {
    int fd = open(EPSON_LOCK, O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    if (flock(fd, LOCK_EX | (wait ? 0 : LOCK_NB)) < 0) { close(fd); return -1; }
    return fd;
}
#endif
