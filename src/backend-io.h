/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef EPSON_BACKEND_IO_H
#define EPSON_BACKEND_IO_H
#include "operation-lock.h"
#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
static inline int epson_fifo_lock(int wait) {
    int fd = open(EPSON_RUNTIME "/fifo.lock", O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    if (flock(fd, LOCK_EX | (wait ? 0 : LOCK_NB)) < 0) {
        int error = errno;
        close(fd); errno = error; return -1;
    }
    return fd;
}
static inline int epson_fifo_open(const char *path) {
    int fd = open(path, O_WRONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
    struct stat st;
    if (fd < 0) return -1;
    if (fstat(fd, &st) < 0) {
        int error = errno;
        close(fd); errno = error; return -1;
    }
    if (!S_ISFIFO(st.st_mode)) { close(fd); errno = EINVAL; return -1; }
    return fd;
}
/* A negative wait_ms allows print backpressure for as long as the reader lives.
 * SIGTERM keeps its default disposition in ecblp, including during poll().
 * Only the unwritten suffix is retried; the FIFO is never reopened on failure.
 * FIFO readiness cannot diagnose USB health; reader loss is EPIPE/POLLERR.
 */
static inline int epson_fifo_write_wait(int fd, const char *p, size_t size,
                                      int wait_ms, size_t *written) {
    size_t total = size;
    const char *stage = "write";
    short revents = 0;
    int error = 0;
    *written = 0;
    while (size) {
        ssize_t n = write(fd, p, size);
        stage = "write"; revents = 0;
        if (n > 0) { p += n; size -= n; *written += n; continue; }
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            struct pollfd watch = {fd, POLLOUT, 0};
            int ready;
            stage = "poll";
            do { ready = poll(&watch, 1, wait_ms); } while (ready < 0 && errno == EINTR);
            revents = watch.revents;
            if (ready < 0) error = errno;
            else if (ready == 0) error = ETIMEDOUT;
            else if (revents & POLLNVAL) error = EBADF;
            else if (revents & (POLLERR | POLLHUP)) error = EPIPE;
            else if (revents & POLLOUT) continue;
            else error = EIO;
        } else {
            error = n < 0 ? errno : EIO;
        }
        fprintf(stderr, "ERROR: ecbd FIFO transfer stage=%s fd=%d errno=%d (%s) poll revents=0x%04x; wrote %zu/%zu bytes%s\n",
                stage, fd, error, strerror(error), (unsigned int)(unsigned short)revents, *written, total,
                error == EPIPE ? "; reader disconnected (check ecbd/USB)" : "");
        errno = error;
        return -1;
    }
    return 0;
}
/* Keep the existing bounded wait for daemon command forwarding. */
static inline int epson_fifo_write(int fd, const char *p, size_t size) {
    size_t written;
    return epson_fifo_write_wait(fd, p, size, 5000, &written);
}
#endif
