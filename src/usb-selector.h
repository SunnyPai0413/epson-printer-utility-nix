/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef EPSON_USB_SELECTOR_H
#define EPSON_USB_SELECTOR_H
/* Filter libusb devices before claiming/detaching any interface. */
static int epson_usb_matches(libusb_device *dev) {
    struct libusb_device_descriptor desc;
    struct libusb_config_descriptor *cfg = NULL;
    const char *product = getenv("EPSON_USB_PRODUCT");
    const char *serial = getenv("EPSON_USB_SERIAL");
    int printer = 0;
    if (libusb_get_device_descriptor(dev, &desc) != 0 || desc.idVendor != VENDOR_ID) return 0;
    if (product && *product && desc.idProduct != strtoul(product, NULL, 16)) return 0;
    if (libusb_get_active_config_descriptor(dev, &cfg) != 0) return 0;
    for (int j = 0; j < cfg->bNumInterfaces; j++)
        for (int k = 0; k < cfg->interface[j].num_altsetting; k++) {
            const struct libusb_interface_descriptor *iface = &cfg->interface[j].altsetting[k];
            if (iface->bInterfaceClass == kUSBPrinterInterfaceClass &&
                iface->bInterfaceSubClass == kUSBPrinterInterfaceSubClass &&
                iface->bInterfaceProtocol == kUSBPrinterInterfaceProtocol) printer = 1;
        }
    libusb_free_config_descriptor(cfg);
    if (!printer) return 0;
    if (serial && *serial) {
        libusb_device_handle *handle = NULL;
        unsigned char text[256];
        if (libusb_open(dev, &handle) != 0) return 0;
        int n = libusb_get_string_descriptor_ascii(handle, desc.iSerialNumber, text, sizeof(text)-1);
        libusb_close(handle);
        if (n <= 0) return 0;
        text[n] = 0;
        if (strcmp((char *)text, serial) != 0) return 0;
    }
    return 1;
}
#endif
