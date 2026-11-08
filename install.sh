#!/bin/sh
# Ubuntu (dracut) install of the imac5k_dp DKMS module for iMac15,1.
# Boot chain (Apple diags.efi -> OpenCore) is assumed to be provided by OCLP.
set -e
[ "$(id -u)" = 0 ] || { echo "run as root: sudo $0" >&2; exit 1; }
H=$(dirname "$(readlink -f "$0")")
V=1.0
K=$(uname -r)

# 1. Kernel module via DKMS (rebuilt automatically on kernel updates).
dkms remove imac5k-dp/$V --all 2>/dev/null || true
rm -rf /usr/src/imac5k-dp-$V
install -d /usr/src/imac5k-dp-$V
install -m644 "$H"/src/* /usr/src/imac5k-dp-$V/
dkms install imac5k-dp/$V -k "$K"

# 2. Load it before amdgpu, both in the initrd and in the real root.
install -m644 "$H/50-imac5k-dp.conf" /etc/modprobe.d/50-imac5k-dp.conf
install -d /usr/lib/dracut/modules.d/95imac5k-dp
install -m755 "$H/dracut/module-setup.sh" /usr/lib/dracut/modules.d/95imac5k-dp/module-setup.sh

# 3. Regenerate the initrd for the running kernel and verify.
dracut --force --kver "$K"

# Root filesystem: modprobe must load imac5k_dp before amdgpu.
deps=$(modprobe -S "$K" --show-depends amdgpu)
echo "$deps" | grep -q 'imac5k_dp' || { echo "ERROR: softdep not effective on rootfs" >&2; exit 1; }

# initrd: only matters if amdgpu itself is loaded from the initrd.
list=$(lsinitrd "/boot/initrd.img-$K")
if echo "$list" | grep -q '/amdgpu\.ko'; then
    echo "$list" | grep -q '/imac5k_dp\.ko' ||
        { echo "ERROR: amdgpu is in the initrd but imac5k_dp is not" >&2; exit 1; }
    echo "OK: amdgpu and imac5k_dp both in initrd."
else
    echo "OK: amdgpu loads from rootfs; softdep there loads imac5k_dp first."
fi

# 4. Re-latch the panel's 5K tiled mode after suspend/resume.
install -m755 "$H/tools/imac5k-latch.py" /usr/local/sbin/imac5k-latch
install -m755 "$H/sleep/imac5k-latch" /usr/lib/systemd/system-sleep/imac5k-latch
echo "Installed resume hook /usr/lib/systemd/system-sleep/imac5k-latch"
echo "Done. Reboot via OpenCore (no nomodeset)."
