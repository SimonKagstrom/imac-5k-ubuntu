#!/bin/bash
# dracut module: put imac5k_dp and the softdep that loads it before amdgpu
# into the initrd. Ubuntu's generic (non-hostonly) dracut does not copy
# /etc/modprobe.d, so the softdep file is installed explicitly.

check() {
    [[ $(cat /sys/class/dmi/id/product_name 2>/dev/null) == "iMac15,1" ]] || return 255
    return 0
}

depends() {
    return 0
}

installkernel() {
    # Safety net: build via DKMS if this kernel does not have the module yet
    # (normally /etc/kernel/postinst.d/dkms has already done so).
    if ! modinfo -k "$kernel" imac5k_dp &>/dev/null && command -v dkms &>/dev/null; then
        dkms install imac5k-dp/1.0 -k "$kernel" >&2 || dwarn "imac5k-dp: DKMS build for $kernel failed"
    fi
    instmods imac5k_dp
}

install() {
    inst_simple /etc/modprobe.d/50-imac5k-dp.conf
}
