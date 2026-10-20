#!/usr/bin/env python3
"""Exit 0 if a serial port carries MAVLink: fcu_probe.py DEVICE BAUD [SECONDS].

Two back-to-back frames whose lengths chain (v1 0xFE / v2 0xFD header) count as MAVLink;
random noise or a console almost never does that twice in a row.
"""
import os, sys, termios, time

dev, baud = sys.argv[1], int(sys.argv[2])
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5

def frame_len(buf, i):
    if buf[i] == 0xFE and i + 1 < len(buf):
        return 8 + buf[i + 1]
    if buf[i] == 0xFD and i + 2 < len(buf):
        return 12 + buf[i + 1] + (13 if buf[i + 2] & 0x01 else 0)
    return None

try:
    fd = os.open(dev, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    attr = termios.tcgetattr(fd)
    speed = getattr(termios, f"B{baud}")
    attr[0] = attr[1] = attr[3] = 0                      # raw: no iflag/oflag/lflag processing
    attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attr[4] = attr[5] = speed
    termios.tcsetattr(fd, termios.TCSANOW, attr)
    termios.tcflush(fd, termios.TCIFLUSH)                # drop bytes received at a previous baud
except (OSError, AttributeError, termios.error):
    sys.exit(2)

buf, end = bytearray(), time.time() + secs
while time.time() < end:
    try:
        buf += os.read(fd, 4096)
    except BlockingIOError:
        time.sleep(0.05)
        continue
    for i in range(len(buf)):
        n = frame_len(buf, i)
        if n and i + n + 1 < len(buf) and frame_len(buf, i + n) is not None:
            sys.exit(0)
sys.exit(1)
