#!/usr/bin/python3 -I
"""Inspect / re-latch the iMac 5K panel's tiled mode via DP AUX (DPCD).

Sequence taken from taprobane99/iMac5KLinux (kernel 7.3 patch):
  root  = eDP link,           DPCD 0x4F1 = 01         -> latch TCON into 2-tile 5K
  slave = second (DP-1) link, DPCD 0x310 = 04 1d 03   -> source table revision

Usage (as root):
  imac5k-latch.py dump    read-only, show relevant registers
  imac5k-latch.py latch   write the latch sequence, then ask DRM to re-detect DP-1
"""
import os
import sys
import time

DRM = "/sys/class/drm"


def find_aux(conn_suffix):
    for c in sorted(os.listdir(DRM)):
        if c.endswith("-" + conn_suffix):
            for e in os.listdir(os.path.join(DRM, c)):
                if e.startswith("drm_dp_aux"):
                    return c, "/dev/" + e
    sys.exit(f"no AUX device for {conn_suffix}")


ROOT_CONN, ROOT_AUX = find_aux("eDP-1")
SLAVE_CONN, SLAVE_AUX = find_aux("DP-1")


def rd(dev, addr, n=1):
    try:
        fd = os.open(dev, os.O_RDONLY)
        try:
            return os.pread(fd, n, addr).hex(" ")
        finally:
            os.close(fd)
    except OSError as e:
        return f"<{e.strerror}>"


def wr(dev, addr, data):
    try:
        fd = os.open(dev, os.O_RDWR)
        try:
            n = os.pwrite(fd, bytes(data), addr)
            return f"ok ({n} bytes)"
        finally:
            os.close(fd)
    except OSError as e:
        return f"<{e.strerror}>"


def status(conn):
    with open(os.path.join(DRM, conn, "status")) as f:
        return f.read().strip()


def dump():
    print(f"root  {ROOT_CONN} {ROOT_AUX}: status={status(ROOT_CONN)}")
    print(f"  DPCD 0x000 rev        : {rd(ROOT_AUX, 0x000)}")
    print(f"  DPCD 0x4F1 latch      : {rd(ROOT_AUX, 0x4F1)}")
    print(f"  DPCD 0x600 power      : {rd(ROOT_AUX, 0x600)}")
    print(f"slave {SLAVE_CONN} {SLAVE_AUX}: status={status(SLAVE_CONN)}")
    print(f"  DPCD 0x000 rev        : {rd(SLAVE_AUX, 0x000)}")
    print(f"  DPCD 0x10A edp cfg    : {rd(SLAVE_AUX, 0x10A)}")
    print(f"  DPCD 0x310 table rev  : {rd(SLAVE_AUX, 0x310, 3)}")
    print(f"  DPCD 0x4F1 latch      : {rd(SLAVE_AUX, 0x4F1)}")
    print(f"  DPCD 0x600 power      : {rd(SLAVE_AUX, 0x600)}")


def latch():
    print("root  0x4F1 <- 01       :", wr(ROOT_AUX, 0x4F1, [0x01]))
    time.sleep(0.2)
    print("slave 0x310 <- 04 1d 03 :", wr(SLAVE_AUX, 0x310, [0x04, 0x1D, 0x03]))
    time.sleep(0.2)
    with open(os.path.join(DRM, SLAVE_CONN, "status"), "w") as f:
        f.write("detect")
    time.sleep(1)
    print(f"{SLAVE_CONN} status now: {status(SLAVE_CONN)}")


if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("run as root")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if cmd == "dump":
        dump()
    elif cmd == "latch":
        dump()
        print("--- latching ---")
        latch()
        print("--- after ---")
        dump()
    else:
        sys.exit(__doc__)
