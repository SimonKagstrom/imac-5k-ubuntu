# imac-5k-ubuntu
This is an ubuntu adapatation of [this reddit thread for OpenSUSE](https://www.reddit.com/r/linux_on_mac/comments/1wyqfbs/the_journey_to_5k_resolution_on_a_2014_imac/)
by AlGoreIsCool. The work in this repo has been written by Claude and tested
on hardware with Ubuntu 26.04.



Native 5120x2880 on the **iMac15,1** (Retina 5K, late 2014 / mid 2015) under
Ubuntu's stock kernel. No custom kernel build is needed and an Ubuntu kernel
update will rebuild the module automatically via DKMS.

Out of the box, Linux drives the iMac's 5K panel as a single 2560x2880 tile,
so you get a stretched picture. This repo keeps the panel in its two-tile 5K
mode with:

- **`imac5k_dp`**, a small DKMS kernel module. When amdgpu tries to power down
  (D3) the panel's DisplayPort receivers, the module replaces that write with
  D0, so the 5K state set up at boot survives. It uses a kprobe on
  `drm_dp_dpcd_write`, filters to AMDGPU AUX channels, and only activates on
  an iMac15,1.
- **A resume hook**. Deep suspend (S3) powers the panel off, and it comes back
  single-tile. After resume, the hook switches the panel back into tiled mode
  with two DPCD register writes over `/dev/drm_dp_aux*`:
  - `0x4F1 = 01` on the eDP link
  - `0x310 = 04 1d 03` on the second DP link

  It then asks DRM to re-detect the second link.

## Tested on

| Model    | GPU                        | Ubuntu       | Kernel           |
|----------|----------------------------|--------------|------------------|
| iMac15,1 | R9 M290X (Pitcairn/GCN 1)  | 26.04.1 LTS  | 7.0.0-43-generic |

Reports from other configurations are welcome.

## Requirements

- **The panel must already be in 5K mode when Linux starts.** Today that means
  booting through Apple's `diags.efi`, which chain-loads
  `.diagnostics/.../Product.efi`. OpenCore Legacy Patcher sets this chain up,
  so if you run OCLP with 5K in macOS, pick Ubuntu from the OpenCore menu.
  (Booting Linux once with `nomodeset` tells you whether the chain is active:
  the console is sharp 5K, just slow.)
- Ubuntu with **dracut** as the initramfs generator (the default on recent
  releases).
- `dkms` and the `linux-generic` metapackage, so headers follow kernel
  updates.

## Install

```bash
sudo apt install dkms linux-headers-generic
sudo ./install.sh
```

Then reboot through OpenCore without `nomodeset`.

`install.sh` does the following:

1. Builds and installs the module via DKMS (`AUTOINSTALL=yes`, so DKMS
   rebuilds it on kernel updates).
2. Installs `/etc/modprobe.d/50-imac5k-dp.conf`
   (`softdep amdgpu pre: imac5k_dp`) and a dracut module, so `imac5k_dp`
   loads before amdgpu.
3. Regenerates the initrd for the running kernel.
4. Installs `/usr/local/sbin/imac5k-latch` and the resume hook
   `/usr/lib/systemd/system-sleep/imac5k-latch`.

## Verify

```bash
sudo dmesg | grep imac5k                         # "armed on drm_dp_dpcd_write..."
cat /sys/module/imac5k_dp/parameters/suppressed  # > 0: D3 writes were blocked
xrandr --listmonitors                            # one 5120x2880 monitor (eDP + DisplayPort-0)
journalctl -t imac5k-latch                       # what the resume hook did
```

To re-latch the panel manually:

```bash
sudo /usr/local/sbin/imac5k-latch dump    # read-only
sudo /usr/local/sbin/imac5k-latch latch
```

## Caveats

- The kprobe assumes `drm_dp_dpcd_write(aux, offset, buffer, size)` and reads
  x86-64 argument registers directly. If a kernel refactor changes that, the
  module silently stops working and you fall back to the stretched picture.
  The machine itself keeps working.
- The panel's DP receivers are never put into D3, so a blanked screen may draw
  slightly more power.
- If you remove macOS, keep the EFI partition that holds the
  `diags.efi` → OpenCore chain, or recreate the chain elsewhere. Otherwise the
  panel will not be in 5K mode at boot.

## Credits

- The `imac5k_dp` kprobe module and the diags.efi boot chain idea come from the
  reddit write-up of the same method (see above). This repo is the Ubuntu adaptation.
- The panel latch sequence (`0x4F1`, `0x310`) comes from
  [taprobane99/iMac5KLinux](https://github.com/taprobane99/iMac5KLinux), which
  solves 5K on several iMac models with a kernel patch. It in turn credits
  [mcirsta/linux-imac-5k](https://github.com/mcirsta/linux-imac-5k).

## License

GPL-2.0. See [LICENSE](LICENSE). The kernel module is GPL-2.0-or-later.
