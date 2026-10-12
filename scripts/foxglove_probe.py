#!/usr/bin/env python3
"""
What does a Foxglove client see on the foxglove_bridge, and does the data flow? Stdlib only (runs on the host: no ROS, no websockets).

    scripts/foxglove_probe.py                                  # 127.0.0.1:8765, every advertised topic
    scripts/foxglove_probe.py -H 100.115.7.84 -f zed           # from the tailnet address, topics containing "zed"
    scripts/foxglove_probe.py -f zed -s /drone_1/zed/zed_node/odom -s /drone_1/chase/image    # also subscribe 6 s: rate and size per message

Connects like the Foxglove app (subprotocol foxglove.sdk.v1, foxglove_bridge >= 3.x), prints serverInfo and the channels the app builds its
Topics list from, then optionally subscribes. Topics missing here are missing in the app (usually a message package the bridge container
lacks: "Failed to load schemaDefinition" in `docker exec bisg-ros cat /tmp/foxglove.log`). Raw 1280x720 images are ~3.6 MB per message:
check `KiB/msg` x Hz against the link before blaming the app; use the `/compressed` image topics remotely.
"""
import argparse
import base64
import json
import os
import socket
import struct
import time

ap = argparse.ArgumentParser()
ap.add_argument("-H", "--host", default="127.0.0.1")
ap.add_argument("-p", "--port", type=int, default=8765)
ap.add_argument("-f", "--filter", default="", help="only list topics containing this text")
ap.add_argument("-s", "--subscribe", action="append", default=[], help="topic to subscribe to (repeatable)")
ap.add_argument("-t", "--seconds", type=float, default=6.0)
args = ap.parse_args()

sock = socket.create_connection((args.host, args.port), timeout=8)
key = base64.b64encode(os.urandom(16)).decode()
sock.sendall((f"GET / HTTP/1.1\r\nHost: {args.host}:{args.port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
              f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: foxglove.sdk.v1\r\n\r\n").encode())
buf = b""
while b"\r\n\r\n" not in buf:
    buf += sock.recv(4096)
head, buf = buf.split(b"\r\n\r\n", 1)
print(head.decode().split("\r\n")[0])


def need(n):
    global buf
    while len(buf) < n:
        chunk = sock.recv(65536)
        if not chunk:
            raise EOFError
        buf += chunk
    out, buf = buf[:n], buf[n:]
    return out


def frame():
    h = need(2)
    fin, op, ln = h[0] >> 7, h[0] & 0x0F, h[1] & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", need(2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", need(8))[0]
    return fin, op, need(ln)


def send_text(txt):
    p, mask = txt.encode(), os.urandom(4)
    hdr = bytes([0x81]) + (bytes([0x80 | len(p)]) if len(p) < 126 else bytes([0x80 | 126]) + struct.pack(">H", len(p)))
    sock.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(p)))


channels, msg, t0 = {}, b"", time.time()
try:
    while time.time() - t0 < 4:        # the server sends serverInfo and the advertise right after the handshake
        fin, op, data = frame()
        if op not in (0, 1, 2):
            continue
        msg += data
        if not fin:
            continue
        if op == 1:
            d = json.loads(msg)
            if d.get("op") == "serverInfo":
                print("server:", d.get("metadata", {}), "capabilities:", d.get("capabilities"))
            elif d.get("op") == "advertise":
                channels.update({c["id"]: c for c in d.get("channels", [])})
        msg = b""
except (EOFError, socket.timeout):
    pass

shown = [c for c in sorted(channels.values(), key=lambda c: c["topic"]) if args.filter in c["topic"]]
print(f"{len(channels)} channels advertised, {len(shown)} match '{args.filter}'")
for c in shown:
    print(f"  {c['topic']}  [{c.get('schemaName')}]")

subs = {}
for i, topic in enumerate(args.subscribe, 1):
    match = [c for c in channels.values() if c["topic"] == topic]
    print(f"subscribe {topic}: " + ("ok" if match else "NOT ADVERTISED"))
    if match:
        subs[i] = match[0]
if subs:
    send_text(json.dumps({"op": "subscribe", "subscriptions": [{"id": i, "channelId": c["id"]} for i, c in subs.items()]}))
    count, size, t1 = {i: 0 for i in subs}, {i: 0 for i in subs}, time.time()
    try:
        while time.time() - t1 < args.seconds:
            fin, op, data = frame()
            if op == 2 and data[0] == 1:   # MessageData: opcode(1) subscriptionId(u32) timestamp(u64) payload
                sid = struct.unpack("<I", data[1:5])[0]
                count[sid] += 1
                size[sid] += len(data) - 13
    except (EOFError, socket.timeout):
        pass
    for i, c in subs.items():
        n = count[i]
        print(f"  {c['topic']}: {n} msgs in {args.seconds:.0f} s = {n / args.seconds:.1f} Hz, {size[i] / max(n, 1) / 1024:.0f} KiB/msg,"
              f" {size[i] / args.seconds / 1e6:.1f} MB/s")
