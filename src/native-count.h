/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef EPSON_NATIVE_COUNT_H
#define EPSON_NATIVE_COUNT_H
#include <stdint.h>
#include <limits.h>
#include <string.h>
/* Original counter API is signed 32 bit with -1 meaning unavailable. */
static inline int epson_count_le(const unsigned char *p) {
    uint32_t n = (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
    return n > INT_MAX ? -1 : (int)n;
}
static inline int epson_count_hex(const char *p) {
    unsigned char bytes[4];
    if (!p || strcspn(p, ";") != 8) return -1;
    for (int i = 0; i < 8; ++i) {
        char c = p[i];
        int n = c >= '0' && c <= '9' ? c-'0' : c >= 'A' && c <= 'F' ? c-'A'+10 : c >= 'a' && c <= 'f' ? c-'a'+10 : -1;
        if (n < 0) return -1;
        if (i % 2) bytes[i/2] |= n; else bytes[i/2] = n << 4;
    }
    return epson_count_le(bytes);
}
#endif
