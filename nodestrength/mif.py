"""Minimal MRtrix3 .mif image reader (header-only + integer / float data).

The MRtrix3 Image Format (MIF) has a plain-ASCII header followed by raw
binary data, optionally in the same file or a sibling. This is enough for
reading the label-volume artefacts (`dk_nodes.mif` etc.) without an
MRtrix3 binary on PATH.

Reference: https://mrtrix.readthedocs.io/en/latest/getting_started/image_data.html
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


# MRtrix datatype tokens → numpy dtype + byte order.
_DTYPE_MAP: Dict[str, Tuple[str, str]] = {
    "UInt8":    ("u1", "|"),
    "Int8":     ("i1", "|"),
    "UInt16LE": ("u2", "<"), "UInt16BE": ("u2", ">"),
    "Int16LE":  ("i2", "<"), "Int16BE":  ("i2", ">"),
    "UInt32LE": ("u4", "<"), "UInt32BE": ("u4", ">"),
    "Int32LE":  ("i4", "<"), "Int32BE":  ("i4", ">"),
    "UInt64LE": ("u8", "<"), "UInt64BE": ("u8", ">"),
    "Int64LE":  ("i8", "<"), "Int64BE":  ("i8", ">"),
    "Float32LE":("f4", "<"), "Float32BE":("f4", ">"),
    "Float64LE":("f8", "<"), "Float64BE":("f8", ">"),
}


@dataclass(frozen=True)
class MifImage:
    data: np.ndarray
    dim: Tuple[int, ...]
    vox: Tuple[float, ...]
    layout: Tuple[int, ...]
    datatype: str
    transform: np.ndarray            # 4x4 affine
    header: Dict[str, List[str]]


def _parse_header(buf: bytes) -> Tuple[Dict[str, List[str]], int]:
    """Parse the ASCII header. Returns (key->list-of-values, byte_offset_of_end+1)."""
    header: Dict[str, List[str]] = {}
    pos = 0
    if not buf.startswith(b"mrtrix image"):
        raise ValueError("Not a MRtrix .mif file (missing 'mrtrix image' magic).")
    # Skip the first line.
    nl = buf.find(b"\n")
    pos = nl + 1

    while True:
        nl = buf.find(b"\n", pos)
        if nl == -1:
            raise ValueError("Truncated header — no 'END' marker.")
        line = buf[pos:nl].decode("ascii", errors="replace").rstrip("\r")
        pos = nl + 1
        if line.strip() == "END":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        header.setdefault(key.strip(), []).append(value.strip())
    return header, pos


def _to_ints(s: str) -> List[int]:
    return [int(x) for x in s.split(",")]


def _to_floats(s: str) -> List[float]:
    return [float(x) for x in s.split(",")]


def read_mif(path: str | Path) -> MifImage:
    """Read a MRtrix3 .mif image, returning a :class:`MifImage` record.

    Currently supports inline-data (`file: . <offset>`) and any of the
    integer/float datatypes in :data:`_DTYPE_MAP`. The returned ``data``
    array is in the storage order on disk; spatial axis orientation
    follows the ``layout`` and ``transform`` fields.
    """
    path = Path(path)
    buf = path.read_bytes()
    header, header_end = _parse_header(buf)

    if "dim" not in header or "datatype" not in header or "file" not in header:
        raise ValueError(f".mif header missing required key(s): {list(header)}")

    dim = tuple(_to_ints(header["dim"][0]))
    vox = tuple(_to_floats(header["vox"][0])) if "vox" in header else (1.0,) * len(dim)
    layout = tuple(int(t) for t in header.get("layout", ["+0,+1,+2"])[0]
                   .replace("+", "").split(","))
    datatype = header["datatype"][0]
    if datatype not in _DTYPE_MAP:
        raise ValueError(f"Unsupported MRtrix datatype: {datatype}")
    np_dtype_kind, byte_order = _DTYPE_MAP[datatype]
    np_dtype = np.dtype(byte_order + np_dtype_kind) if byte_order != "|" else np.dtype(np_dtype_kind)

    # file: ". <offset>" means data is inline at the given byte offset.
    file_line = header["file"][0]
    parts = file_line.split()
    if not parts or parts[0] != ".":
        raise NotImplementedError("External-file .mif data not supported; got "
                                  f"'{file_line}'")
    data_offset = int(parts[1]) if len(parts) > 1 else header_end
    raw = buf[data_offset:]
    arr = np.frombuffer(raw, dtype=np_dtype, count=int(np.prod(dim)))
    arr = arr.reshape(dim, order="F")  # MRtrix uses Fortran order

    # Build the 4x4 affine from the 3 'transform: ...' rows + voxel sizes.
    transform = np.eye(4)
    if "transform" in header:
        rows = [_to_floats(r) for r in header["transform"]]
        for i, r in enumerate(rows[:3]):
            for j, v in enumerate(r):
                transform[i, j] = v
        # Multiply rotation columns by voxel sizes.
        for j in range(3):
            transform[:3, j] *= vox[j] if j < len(vox) else 1.0

    return MifImage(
        data=arr, dim=dim, vox=vox, layout=layout,
        datatype=datatype, transform=transform, header=header,
    )
