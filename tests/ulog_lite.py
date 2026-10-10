"""
Minimal PX4 ULog reader (numpy only): `read(path, topics) -> {name: {field: np.ndarray}}`.

Enough for test analysis (definitions + data messages, multi-instance topics as `name` for instance 0 and `name.N` for
the others); no parameters, logging strings or appended data. Format: docs.px4.io/main/en/dev_log/ulog_file_format.
Exists because no image here ships pyulog and test containers do not install packages.
"""
import struct

import numpy as np

_BASIC = {
    "int8_t": "i1", "uint8_t": "u1", "int16_t": "<i2", "uint16_t": "<u2", "int32_t": "<i4", "uint32_t": "<u4",
    "int64_t": "<i8", "uint64_t": "<u8", "float": "<f4", "double": "<f8", "bool": "u1", "char": "S1",
}


def _dtype(name, formats, cache):
    if name in cache:
        return cache[name]
    fields = []
    for item in formats[name]:
        ftype, fname = item
        count = 1
        if "[" in ftype:
            ftype, count = ftype[:-1].split("[")
            count = int(count)
        base = np.dtype(_BASIC[ftype]) if ftype in _BASIC else _dtype(ftype, formats, cache)
        fields.append((fname, base, (count,)) if count > 1 else (fname, base))
    cache[name] = np.dtype(fields)          # packed: ULog structs carry explicit _padding fields
    return cache[name]


def read(path, topics=None):
    """Return {topic[.instance]: {field: array}}; nested and array fields are flattened to `a.b` / `a[i]`."""
    with open(path, "rb") as fh:
        buf = fh.read()
    if buf[:7] != b"ULog\x01\x12\x35":
        raise ValueError(f"{path}: not a ULog file")
    pos = 16
    formats, subs, chunks = {}, {}, {}
    want = set(topics) if topics else None
    n = len(buf)
    while pos + 3 <= n:
        size, kind = struct.unpack_from("<HB", buf, pos)
        body = buf[pos + 3: pos + 3 + size]
        pos += 3 + size
        if len(body) < size:
            break                                           # truncated tail (log still being written)
        if kind == ord("F"):
            text = body.decode("ascii", "replace")
            fname, spec = text.split(":", 1)
            formats[fname] = [tuple(f.split(" ", 1)) for f in spec.split(";") if f]
        elif kind == ord("A"):
            multi_id, msg_id = struct.unpack_from("<BH", body, 0)
            tname = body[3:].decode("ascii", "replace")
            if want is None or tname in want:
                subs[msg_id] = (tname, multi_id)
        elif kind == ord("D"):
            msg_id = struct.unpack_from("<H", body, 0)[0]
            if msg_id in subs:
                chunks.setdefault(msg_id, []).append(body[2:])
    out, cache = {}, {}
    for msg_id, (tname, multi_id) in subs.items():
        rows = chunks.get(msg_id)
        if not rows:
            continue
        dt = _dtype(tname, formats, cache)
        # the last padding field may be cut off in the file: pad every row to the struct size
        raw = b"".join(r.ljust(dt.itemsize, b"\0")[:dt.itemsize] for r in rows)
        arr = np.frombuffer(raw, dtype=dt)
        key = tname if multi_id == 0 else f"{tname}.{multi_id}"
        out[key] = _flatten(arr)
    return out


def _flatten(arr, prefix=""):
    cols = {}
    for name in arr.dtype.names:
        if name.startswith("_padding"):
            continue
        col = arr[name]
        if col.dtype.names:
            cols.update(_flatten(col, f"{prefix}{name}."))
        elif col.ndim > 1:
            for i in range(col.shape[1]):
                cols[f"{prefix}{name}[{i}]"] = col[:, i]
        else:
            cols[f"{prefix}{name}"] = col
    return cols
