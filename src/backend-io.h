/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef EPSON_BACKEND_IO_H
#define EPSON_BACKEND_IO_H
#include "operation-lock.h"
#include <errno.h>
#include <poll.h>
#include <sys/stat.h>
static inline int epson_fifo_lock(int wait) {
    int fd = open(EPSON_RUNTIME "/fifo.lock", O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    if (flock(fd, LOCK_EX | (wait ? 0 : LOCK_NB)) < 0) { close(fd); return -1; }
    return fd;
}
static inline int epson_fifo_open(const char *path) {
    int fd = open(path, O_WRONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
    struct stat st;
    if (fd < 0) return -1;
    if (fstat(fd, &st) || !S_ISFIFO(st.st_mode)) { close(fd); return -1; }
    return fd;
}
static inline int epson_fifo_write(int fd, const char *p, size_t size) {
    while (size) {
        ssize_t n = write(fd, p, size);
        if (n > 0) { p += n; size -= n; continue; }
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            struct pollfd watch = {fd, POLLOUT, 0};
            if (poll(&watch, 1, 5000) > 0 && !(watch.revents & (POLLERR | POLLHUP))) continue;
        }
        return -1; /* Failure after a partial write is never replayed. */
    }
    return 0;
}
#endif
