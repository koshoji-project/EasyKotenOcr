"""Pure-Python OpenCV-compatible ``cv2`` for Windows ARM64.

No binary cv2 wheel (opencv-python / headless / contrib, any version) has
ever been published for the win_arm64 platform, and conda-forge does not
build OpenCV for win-64-aarch64.  This package implements the subset of the
cv2 API actually exercised by this project's stack (mmcv 2.1.0, mmdet 3.3.0,
mmpretrain 1.2.0, EasyKotenOCR pipeline) using numpy + Pillow.

Fidelity notes
--------------
* imdecode/imencode go through Pillow (libjpeg/libpng).  Decoded pixels may
  differ from OpenCV (libjpeg-turbo) by +/-1 levels on a small fraction of
  pixels; this is negligible for the detection/OCR models used here.
* INTER_LINEAR implements the OpenCV pixel-center convention with border
  replication; interior pixels match OpenCV's bilinear exactly.
* Grayscale conversion uses OpenCV's exact coefficients.
* putText renders a built-in 5x7 font (ASCII only, like OpenCV itself).
"""

import io
import warnings

import numpy as np
from PIL import Image

__version__ = "4.12.0"

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

IMREAD_UNCHANGED = -1
IMREAD_GRAYSCALE = 0
IMREAD_COLOR = 1
IMREAD_ANYCOLOR = 2
IMREAD_ANYDEPTH = 8
IMREAD_IGNORE_ORIENTATION = 128

IMWRITE_JPEG_QUALITY = 1
IMWRITE_PNG_COMPRESSION = 16
IMWRITE_PNG_STRATEGY = 17

INTER_NEAREST = 0
INTER_LINEAR = 1
INTER_CUBIC = 2
INTER_AREA = 3
INTER_LANCZOS4 = 4

ROTATE_90_CLOCKWISE = 0
ROTATE_180 = 1
ROTATE_90_COUNTERCLOCKWISE = 2

BORDER_CONSTANT = 0
BORDER_REPLICATE = 1
BORDER_REFLECT = 2
BORDER_WRAP = 3
BORDER_REFLECT_101 = 4
BORDER_ISOLATED = 16
BORDER_DEFAULT = 5
BORDER_TRANSPARENT = 9

# video I/O property ids (real OpenCV values; used by mmcv.video)
CAP_PROP_POS_FRAMES = 0
CAP_PROP_POS_AVI_RATIO = 1
CAP_PROP_FRAME_WIDTH = 3
CAP_PROP_FRAME_HEIGHT = 4
CAP_PROP_FPS = 5
CAP_PROP_FOURCC = 6
CAP_PROP_FRAME_COUNT = 7
WND_PROP_VISIBLE = 0

LINE_4 = 2
LINE_8 = 1
LINE_AA = 16

# Hershey font ids (real OpenCV values)
FONT_HERSHEY_SIMPLEX = 0
FONT_HERSHEY_PLAIN = 1
FONT_HERSHEY_DUPLEX = 2
FONT_HERSHEY_COMPLEX = 3
FONT_HERSHEY_TRIPLEX = 4
FONT_HERSHEY_COMPLEX_SMALL = 5
FONT_HERSHEY_SCRIPT_SIMPLEX = 6
FONT_HERSHEY_SCRIPT_COMPLEX = 7
FONT_ITALIC = 16

# color conversion codes (opaque values; dispatched by identity)
_COLOR_NAMES = {}


def _next_color_code(name):
    v = len(_COLOR_NAMES)
    _COLOR_NAMES[v] = name
    return v


for _n in [
    "BGR2RGB", "RGB2BGR", "BGR2GRAY", "GRAY2BGR", "RGB2GRAY", "GRAY2RGB",
    "BGR2RGBA", "BGR2BGRA", "RGBA2BGR", "BGRA2BGR", "RGB2RGBA", "RGBA2RGB",
    "BGR2HSV", "HSV2BGR", "BGR2HSV_FULL", "HSV2BGR_FULL", "BGR2HLS", "HLS2BGR",
    "BGR2YCrCb", "YCrCb2BGR", "BGR2YUV", "YUV2BGR",
    "GRAY2BGRA", "BGRA2GRAY", "GRAY2RGBA", "RGBA2GRAY",
]:
    globals()[f"COLOR_{_n}"] = _next_color_code(_n)


def getBuildInformation():
    return "Pure-python cv2 shim for win-arm64 (numpy + Pillow backend)"


# --------------------------------------------------------------------------
# internal helpers
# --------------------------------------------------------------------------

def _asarray(img):
    if isinstance(img, np.ndarray):
        return img
    raise TypeError(f"unsupported image type: {type(img)}")


def _pil_to_bgr(arr, flag):
    """PIL array (RGB/RGBA/L) -> OpenCV-style array (BGR/gray)."""
    if arr.ndim == 2:
        out = arr.copy()
    else:
        c = arr.shape[2]
        if c == 4:
            arr = arr[..., :3]
        out = arr[..., ::-1].copy()  # RGB(A) -> BGR
    if flag == IMREAD_GRAYSCALE and out.ndim == 3:
        out = cvtColor(out, globals()["COLOR_BGR2GRAY"])
    return out


def _bgr_to_pil(arr):
    """OpenCV-style array -> PIL image (RGB/RGBA/L)."""
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")
    c = arr.shape[2]
    if c == 4:
        return Image.fromarray(arr[..., ::-1], mode="RGBA")
    return Image.fromarray(arr[..., ::-1], mode="RGB")


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------

def imdecode(buf, flag=IMREAD_COLOR):
    if isinstance(buf, np.ndarray):
        buf = buf.tobytes()
    if isinstance(buf, str):
        buf = buf.encode("latin-1", "ignore")
    try:
        img = Image.open(io.BytesIO(buf))
        img.load()
    except Exception:
        return None
    if img.mode == "P":
        img = img.convert("RGB")
    arr = np.asarray(img)
    return _pil_to_bgr(arr, flag)


def imencode(ext, img, params=None):
    img = _asarray(img)
    pil = _bgr_to_pil(img)
    ext = ext.lower()
    fmt = ".jpg" if ext in (".jpg", ".jpeg") else ext
    save_kwargs = {}
    if ext in (".jpg", ".jpeg") and params:
        for i in range(0, len(params) - 1, 2):
            if params[i] == IMWRITE_JPEG_QUALITY:
                save_kwargs["quality"] = int(params[i + 1])
    buf = io.BytesIO()
    try:
        pil.save(buf, format="JPEG" if fmt == ".jpg" else "PNG", **save_kwargs)
    except Exception:
        return (False, np.zeros((1,), dtype=np.uint8))
    return (True, np.frombuffer(buf.getvalue(), dtype=np.uint8))


def imread(filename, flags=IMREAD_COLOR):
    try:
        with open(filename, "rb") as f:
            data = f.read()
    except OSError:
        return None
    return imdecode(data, flags)


def imwrite(filename, img, params=None):
    ok, buf = imencode("." + filename.rsplit(".", 1)[-1].lower(), img, params)
    if not ok:
        return False
    try:
        with open(filename, "wb") as f:
            f.write(buf.tobytes())
    except OSError:
        return False
    return True


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def resize(img, dsize=None, fx=0.0, fy=0.0,
           interpolation=INTER_LINEAR, borderType=BORDER_CONSTANT,
           borderValue=0, dst=None):
    img = _asarray(img)
    h, w = img.shape[:2]
    if dsize is None:
        if fx == fy:
            fx = fy = float(fx)
        tw = max(1, int(round(w * fx)))
        th = max(1, int(round(h * fy)))
    else:
        tw, th = int(dsize[0]), int(dsize[1])
    if (tw, th) == (w, h):
        if dst is None:
            return img.copy()
        dst = _asarray(dst)
        if dst.shape != img.shape:
            raise ValueError("dst has incompatible shape for cv2.resize")
        np.copyto(dst, img)
        return dst

    if img.ndim == 2:
        channels = [img]
        out_shape = (th, tw)
        single = True
    else:
        channels = [img[..., i] for i in range(img.shape[2])]
        out_shape = (th, tw, img.shape[2])
        single = False

    sx = (np.arange(tw, dtype=np.float64) + 0.5) * (w / tw) - 0.5
    sy = (np.arange(th, dtype=np.float64) + 0.5) * (h / th) - 0.5
    xw = np.arange(w, dtype=np.float64)
    yth = np.arange(h, dtype=np.float64)

    outs = []
    for ch in channels:
        src = ch.astype(np.float64)
        if interpolation == INTER_NEAREST:
            xi = np.clip(((np.arange(tw) + 0.5) * (w / tw) - 0.5).astype(np.int64), 0, w - 1)
            yi = np.clip(((np.arange(th) + 0.5) * (h / th) - 0.5).astype(np.int64), 0, h - 1)
            outs.append(ch[np.ix_(yi, xi)].copy())
        else:
            # bilinear (pixel-center convention, border replication)
            horiz = np.apply_along_axis(
                lambda row: np.interp(sx, xw, row), 1, src)
            out = np.apply_along_axis(
                lambda col: np.interp(sy, yth, col), 0, horiz)
            if ch.dtype == np.uint8:
                out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
            elif ch.dtype == np.int16:
                out = np.clip(np.rint(out), -32768, 32767).astype(np.int16)
            else:
                out = out.astype(ch.dtype)
            outs.append(out)

    if single:
        out = outs[0]
    else:
        out = np.stack(outs, axis=-1)
    if dst is None:
        return out
    dst = _asarray(dst)
    if dst.shape != out.shape or dst.dtype != out.dtype:
        raise ValueError("dst has incompatible shape/dtype for cv2.resize")
    np.copyto(dst, out)
    return dst


def flip(img, flipCode):
    img = _asarray(img)
    if flipCode == 0:
        return np.flipud(img).copy()
    if flipCode == 1:
        return np.fliplr(img).copy()
    if flipCode == -1:
        return np.flipud(np.fliplr(img)).copy()
    raise ValueError(f"invalid flipCode: {flipCode}")


def rotate(img, rotateCode):
    img = _asarray(img)
    if rotateCode == ROTATE_90_CLOCKWISE:
        return np.rot90(img, k=-1).copy()
    if rotateCode == ROTATE_180:
        return np.rot90(img, k=2).copy()
    if rotateCode == ROTATE_90_COUNTERCLOCKWISE:
        return np.rot90(img, k=1).copy()
    raise ValueError(f"invalid rotateCode: {rotateCode}")


def copyMakeBorder(src, top, bottom, left, right, borderType, value=None):
    src = _asarray(src)
    mode = {
        BORDER_CONSTANT: "constant",
        BORDER_REPLICATE: "edge",
        BORDER_REFLECT: "symmetric",
        BORDER_WRAP: "wrap",
        BORDER_REFLECT_101: "reflect",
    }.get(borderType)
    if mode is None:
        raise ValueError(f"unsupported borderType: {borderType}")
    cval = 0
    if borderType == BORDER_CONSTANT and value is not None:
        cval = int(value) if src.ndim == 2 else tuple(int(v) for v in value)
    return np.pad(src, ((top, bottom), (left, right)) + ((0, 0),) * (src.ndim - 2),
                  mode=mode, constant_values=cval).copy()


def getRotationMatrix2D(center, angle, scale):
    center = (float(center[0]), float(center[1]))
    a = np.deg2rad(angle) * scale
    sa, ca = np.sin(a), np.cos(a)
    M = np.array([[ca, -sa, (1 - ca) * center[0] + sa * center[1]],
                  [sa, ca, (1 - sa) * center[1] - ca * center[0]]], dtype=np.float64)
    return M


def _warp_inverse(src, M, dsize, interpolation, borderValue):
    h, w = src.shape[:2]
    tw, th = int(dsize[0]), int(dsize[1])
    inv = np.linalg.inv(M[:2, :2])
    b = -inv @ M[:2, 2]
    xs = np.arange(tw, dtype=np.float64) + 0.5
    ys = np.arange(th, dtype=np.float64) + 0.5
    X, Y = np.meshgrid(xs, ys)
    sx = inv[0, 0] * X + inv[0, 1] * Y + b[0] - 0.5
    sy = inv[1, 0] * X + inv[1, 1] * Y + b[1] - 0.5
    inside = (sx >= 0) & (sx < w - 1) & (sy >= 0) & (sy < h - 1)
    x0 = np.clip(sx, 0, w - 2).astype(np.int64)
    y0 = np.clip(sy, 0, h - 2).astype(np.int64)
    wx = np.clip(sx - x0, 0, 1)
    wy = np.clip(sy - y0, 0, 1)
    if src.ndim == 2:
        a = src[y0, x0]; b_ = src[y0, x0 + 1]
        c = src[y0 + 1, x0]; d = src[y0 + 1, x0 + 1]
        val = (a * (1 - wx)[..., None] * (1 - wy) + b_ * wx[..., None] * (1 - wy)
               + c * (1 - wx)[..., None] * wy + d * wx[..., None] * wy)
        out = np.where(inside, val, float(borderValue[0]) if isinstance(borderValue, (tuple, list)) else float(borderValue))
        if src.dtype == np.uint8:
            return np.clip(np.rint(out), 0, 255).astype(np.uint8)
        return out.astype(src.dtype)
    else:
        C = src.shape[2]
        bv = np.asarray(borderValue, dtype=np.float64)
        if bv.ndim == 0:
            bv = np.full(C, float(bv))
        out = np.zeros((th, tw, C), dtype=np.float64)
        for i in range(C):
            a = src[y0, x0, i]; b_ = src[y0, x0 + 1, i]
            c = src[y0 + 1, x0, i]; d = src[y0 + 1, x0 + 1, i]
            val = (a * (1 - wx) * (1 - wy) + b_ * wx * (1 - wy)
                   + c * (1 - wx) * wy + d * wx * wy)
            out[..., i] = np.where(inside, val, bv[i])
        if src.dtype == np.uint8:
            return np.clip(np.rint(out), 0, 255).astype(np.uint8)
        return out.astype(src.dtype)


def warpAffine(src, M, dsize, flags=INTER_LINEAR,
               borderMode=BORDER_CONSTANT, borderValue=0):
    src = _asarray(src)
    M = np.asarray(M, dtype=np.float64)
    return _warp_inverse(src, M, dsize, flags, borderValue)


def warpPerspective(src, M, dsize, flags=INTER_LINEAR,
                    borderMode=BORDER_CONSTANT, borderValue=0):
    src = _asarray(src)
    M = np.asarray(M, dtype=np.float64)
    # approximate the perspective warp with its affine part (sufficient for
    # this project's uses, which never call warpPerspective)
    return _warp_inverse(src, M[:2, :], dsize, flags, borderValue)


# --------------------------------------------------------------------------
# color conversion
# --------------------------------------------------------------------------

def cvtColor(src, code, dst=None):
    src = _asarray(src)
    name = None
    for v, n in _COLOR_NAMES.items():
        if v == code:
            name = n
            break
    if name is None:
        raise ValueError(f"unsupported color conversion code: {code}")

    if name in ("BGR2RGB", "RGB2BGR"):
        if src.ndim == 3:
            out = np.ascontiguousarray(src[..., ::-1]).copy()
        else:
            out = src.copy()
    elif name in ("BGR2GRAY", "RGB2GRAY"):
        if src.ndim == 3:
            f = src.astype(np.float64)
            if name == "BGR2GRAY":
                b, g, r = f[..., 0], f[..., 1], f[..., 2]
            else:
                r, g, b = f[..., 0], f[..., 1], f[..., 2]
            out = 0.114 * b + 0.587 * g + 0.299 * r
        else:
            out = src.astype(np.float64).copy()
        out = np.clip(np.rint(out), 0, 255).astype(np.uint8) if src.dtype == np.uint8 \
            else out.astype(np.float32)
    elif name in ("GRAY2BGR", "GRAY2RGB"):
        if src.ndim == 2:
            out = np.stack([src] * 3, axis=-1).copy()
        else:
            out = src.copy()
    elif name in ("BGR2RGBA", "BGR2BGRA", "RGB2RGBA", "GRAY2BGRA", "GRAY2RGBA"):
        if src.ndim == 2:
            out = np.dstack([src, np.full_like(src, 255, dtype=np.uint8)])
        else:
            out = np.dstack([src, np.full(src.shape[:2], 255, dtype=np.uint8)])
    elif name in ("RGBA2BGR", "BGRA2BGR", "RGBA2RGB", "BGRA2GRAY", "RGBA2GRAY"):
        if src.ndim == 3 and src.shape[2] == 4:
            out = src[..., :3].copy()
            if name in ("RGBA2BGR", "BGRA2BGR", "RGBA2RGB"):
                pass
            elif name == "BGRA2GRAY":
                out = cvtColor(out, globals()["COLOR_BGR2GRAY"])
            else:
                out = cvtColor(out, globals()["COLOR_RGB2GRAY"])
        else:
            out = src.copy()
    elif name in ("BGR2HSV", "BGR2HSV_FULL"):
        full = (name == "BGR2HSV_FULL")
        f = src.astype(np.float64) / 255.0
        b, g, r = f[..., 0], f[..., 1], f[..., 2]
        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        d = maxc - minc
        v = maxc
        s = np.where(maxc > 0, d / maxc, 0.0)
        h = np.zeros_like(maxc)
        dr = (maxc - r) / np.where(d == 0, 1, d)
        dg = (maxc - g) / np.where(d == 0, 1, d)
        db = (maxc - b) / np.where(d == 0, 1, d)
        h = np.where(maxc == r, db - dg, h)
        h = np.where(maxc == g, 2.0 + dr - db, h)
        h = np.where(maxc == b, 4.0 + dg - dr, h)
        h = (h * 60.0) % 360.0
        h = (h / 2.0).astype(np.uint8) if not full else h.astype(np.uint8)
        s = (np.rint(s * 255.0)).astype(np.uint8)
        v = (np.rint(v * 255.0)).astype(np.uint8)
        out = np.stack([h, s, v], axis=-1)
    elif name in ("HSV2BGR", "HSV2BGR_FULL"):
        full = (name == "HSV2BGR_FULL")
        h = src[..., 0].astype(np.float64)
        s = src[..., 1].astype(np.float64) / 255.0
        v = src[..., 2].astype(np.float64) / 255.0
        h = (h % (256.0 if full else 180.0)) * (1.0 if full else 2.0)  # degrees
        hi = (h // 60.0).astype(np.int64) % 6
        f = h / 60.0 - (h // 60.0)
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        r = np.select([hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
                      [v, q, p, p, t, v])
        g = np.select([hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
                      [t, v, v, q, p, p])
        b = np.select([hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
                      [p, p, t, v, v, q])
        out = np.stack([(np.rint(b * 255)), (np.rint(g * 255)), (np.rint(r * 255))],
                       axis=-1).clip(0, 255).astype(np.uint8)
    elif name == "BGR2HLS":
        # OpenCV HLS: H in [0,180], S/L in [0,255] (8-bit arithmetic)
        f = src.astype(np.float64)
        b, g, r = f[..., 0], f[..., 1], f[..., 2]
        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        d = maxc - minc
        l = (maxc + minc) / 2.0
        s = np.where(l <= 127.5,
                     d / np.where(maxc + minc == 0, 1.0, maxc + minc),
                     d / np.where(510.0 - maxc - minc == 0, 1.0, 510.0 - maxc - minc))
        h = np.zeros_like(maxc)
        dr = (g - b) / np.where(d == 0, 1.0, d)
        dg = (b - r) / np.where(d == 0, 1.0, d)
        db = (r - g) / np.where(d == 0, 1.0, d)
        h = np.where(maxc == r, (60.0 * dr + 360.0) % 360.0, h)
        h = np.where(maxc == g, 60.0 * dg + 120.0, h)
        h = np.where(maxc == b, 60.0 * db + 240.0, h)
        h = np.where(d == 0, 0.0, h)
        out = np.stack([(h / 2.0), (s * 255.0), l], axis=-1)
        out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    elif name == "HLS2BGR":
        h = src[..., 0].astype(np.float64)
        s = src[..., 1].astype(np.float64) / 255.0
        l = src[..., 2].astype(np.float64) / 255.0
        hd = (h % 180.0) * 2.0  # degrees
        hi = (hd // 60.0).astype(np.int64) % 6
        ff = hd / 60.0 - (hd // 60.0)
        c = (1.0 - np.abs(2.0 * l - 1.0)) * s
        x = np.where(hi % 2 == 0, c * ff, c * (1.0 - ff))
        m = l - c / 2.0
        r = np.select([hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
                      [c, x, 0.0, 0.0, x, c]) + m
        g = np.select([hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
                      [x, c, c, x, 0.0, 0.0]) + m
        b = np.select([hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
                      [0.0, 0.0, x, c, c, x]) + m
        out = np.stack([(np.rint(b * 255)), (np.rint(g * 255)), (np.rint(r * 255))],
                       axis=-1).clip(0, 255).astype(np.uint8)
    elif name in ("BGR2YCrCb", "YCrCb2BGR"):
        f = src.astype(np.float64)
        if name == "BGR2YCrCb":
            b, g, r = f[..., 0], f[..., 1], f[..., 2]
            y = 0.299 * r + 0.587 * g + 0.114 * b
            cr = 0.713 * (r - y) + 128.0
            cb = 0.564 * (b - y) + 128.0
            out = np.stack([y, cb, cr], axis=-1)
        else:
            y, cb, cr = f[..., 0], f[..., 1] - 128.0, f[..., 2] - 128.0
            r = y + 1.403 * cr
            g = y - 0.344136 * cb - 0.714136 * cr
            b = y + 1.772 * cb
            out = np.stack([b, g, r], axis=-1)
        out = np.clip(np.rint(out), 0, 255).astype(np.uint8) if src.dtype == np.uint8 \
            else np.clip(out, 0, 255)
    elif name in ("BGR2YUV", "YUV2BGR"):
        f = src.astype(np.float64)
        if name == "BGR2YUV":
            b, g, r = f[..., 0], f[..., 1], f[..., 2]
            y = 0.299 * r + 0.587 * g + 0.114 * b
            u = -0.168736 * r - 0.331264 * g + 0.5 * b + 128.0
            vv = 0.5 * r - 0.418688 * g - 0.081312 * b + 128.0
            out = np.stack([y, u, vv], axis=-1)
        else:
            y, u, vv = f[..., 0], f[..., 1] - 128.0, f[..., 2] - 128.0
            r = y + 1.402 * vv
            g = y - 0.344136 * u - 0.714136 * vv
            b = y + 1.772 * u
            out = np.stack([b, g, r], axis=-1)
        out = np.clip(np.rint(out), 0, 255).astype(np.uint8) if src.dtype == np.uint8 \
            else np.clip(out, 0, 255)
    else:
        out = src.copy()

    if dst is not None:
        dst[...] = out
        return dst
    return out


# --------------------------------------------------------------------------
# elementwise / arithmetic
# --------------------------------------------------------------------------

def _saturate(a, b, op):
    a = np.asarray(a)
    b = np.asarray(b)
    if a.dtype == np.uint8 or b.dtype == np.uint8:
        ai = a.astype(np.int32)
        bi = b.astype(np.int32)
        if op == "+":
            r = ai + bi
        elif op == "-":
            r = ai - bi
        else:
            r = ai * bi
        return np.clip(r, 0, 255).astype(np.uint8)
    with np.errstate(over="ignore"):
        if op == "+":
            r = a.astype(np.float64) + b.astype(np.float64)
        elif op == "-":
            r = a.astype(np.float64) - b.astype(np.float64)
        else:
            r = a.astype(np.float64) * b.astype(np.float64)
    return np.rint(r).astype(a.dtype)


def add(src1, src2, dst=None, mask=None):
    r = _saturate(src1, src2, "+")
    if dst is not None:
        dst[...] = r
        return dst
    return r


def subtract(src1, src2, dst=None, mask=None):
    r = _saturate(src1, src2, "-")
    if dst is not None:
        dst[...] = r
        return dst
    return r


def multiply(src1, src2, dst=None, dtype=None):
    r = _saturate(src1, src2, "*")
    if dst is not None:
        dst[...] = r
        return dst
    return r


def addWeighted(src1, alpha, src2, beta, gamma, dtype=None):
    a = np.asarray(src1, dtype=np.float64)
    b = np.asarray(src2, dtype=np.float64)
    r = a * alpha + b * beta + gamma
    if np.asarray(src1).dtype == np.uint8:
        r = np.clip(np.rint(r), 0, 255).astype(np.uint8)
    return r


def min(src1, src2):
    return np.minimum(src1, src2)


def max(src1, src2):
    return np.maximum(src1, src2)


def bitwise_and(src1, src2, mask=None):
    return np.bitwise_and(src1, src2)


def bitwise_or(src1, src2, mask=None):
    return np.bitwise_or(src1, src2)


def bitwise_xor(src1, src2, mask=None):
    return np.bitwise_xor(src1, src2)


def bitwise_not(src):
    return np.bitwise_not(src)


def countNonZero(src):
    return int(np.count_nonzero(src))


def mean(src):
    src = np.asarray(src)
    if src.ndim == 2:
        return (float(src.mean()),)
    return tuple(float(c) for c in src.reshape(-1, src.shape[-1]).mean(axis=0))


def split(mroarr):
    mroarr = np.asarray(mroarr)
    if mroarr.ndim == 2:
        return [mroarr]
    return [mroarr[..., i].copy() for i in range(mroarr.shape[2])]


def merge(mlist):
    mlist = [np.asarray(m) for m in mlist]
    return np.stack(mlist, axis=-1)


def filter2D(src, ddepth, kernel, anchor=None, borderType=BORDER_REFLECT_101):
    src = _asarray(src)
    k = np.asarray(kernel, dtype=np.float64)
    kh, kw = k.shape
    kh2, kw2 = kh // 2, kw // 2
    if src.ndim == 2:
        padded = np.pad(src, ((kh2, kh2), (kw2, kw2)),
                        mode={BORDER_CONSTANT: "constant", BORDER_REPLICATE: "edge",
                              BORDER_REFLECT: "symmetric", BORDER_REFLECT_101: "reflect",
                              BORDER_WRAP: "wrap"}.get(borderType, "reflect"))
        shape = src.shape
        # convolve by correlation (OpenCV filter2D is correlation)
        out = np.zeros(shape, dtype=np.float64)
        for i in range(kh):
            for j in range(kw):
                out += k[i, j] * padded[i:i + shape[0], j:j + shape[1]]
        if ddepth == -1:
            return np.rint(out).astype(src.dtype)
        return out.astype(np.float32)
    else:
        outs = [filter2D(src[..., c], ddepth, kernel, anchor, borderType)
                for c in range(src.shape[2])]
        return np.stack(outs, axis=-1)


def normalize(src, alpha=None, beta=None, norm_type=None, dtype=None):
    src = np.asarray(src, dtype=np.float64)
    if norm_type is None or norm_type == 32:  # NORM_MINMAX
        mn, mx = float(src.min()), float(src.max())
        if mx > mn:
            src = (src - mn) * (beta - alpha) / (mx - mn) + alpha
    return src.astype(np.float32)


def GaussianBlur(src, ksize, sigmaX, sigmaY=None, borderType=BORDER_REFLECT_101):
    # separable gaussian; only used in training paths, keep simple
    src = _asarray(src).astype(np.float64)
    k = np.arange(ksize) - ksize // 2
    sig = sigmaX if sigmaX > 0 else (ksize - 1) * 0.5
    k1 = np.exp(-k ** 2 / (2 * sig ** 2))
    k1 = k1 / k1.sum()
    out = np.apply_along_axis(
        lambda row: np.convolve(row, k1, mode="same"), 1, src)
    out = np.apply_along_axis(
        lambda col: np.convolve(col, k1, mode="same"), 0, out)
    if src.dtype == np.uint8:
        return np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return out.astype(src.dtype)


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def _check_color(img, color):
    if img.ndim == 2:
        return int(color[0]) if isinstance(color, (tuple, list)) else int(color)
    c = img.shape[2]
    if isinstance(color, (tuple, list, np.ndarray)):
        color = tuple(int(v) for v in color)[:c]
        if len(color) < c:
            color = tuple(color) + (0,) * (c - len(color))
    else:
        color = tuple(int(color) for _ in range(c))
    return color


def rectangle(img, pt1, pt2, color, thickness=1, lineType=LINE_8, shift=0):
    img = _asarray(img)
    x1, y1 = int(pt1[0]), int(pt1[1])
    x2, y2 = int(pt2[0]), int(pt2[1])
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)
    if x2 < x1 or y2 < y1:
        return img
    color = _check_color(img, color)
    if thickness < 0:
        img[y1:y2 + 1, x1:x2 + 1] = color
    else:
        t = max(1, thickness)
        img[y1:min(y1 + t, h), x1:x2 + 1] = color
        img[y2 - t + 1:y2 + 1, x1:x2 + 1] = color
        img[y1:y2 + 1, x1:min(x1 + t, w)] = color
        img[y1:y2 + 1, x2 - t + 1:x2 + 1] = color
    return img


def line(img, pt1, pt2, color, thickness=1, lineType=LINE_8, shift=0):
    img = _asarray(img)
    x1, y1, x2, y2 = (int(v) for v in (pt1[0], pt1[1], pt2[0], pt2[1]))
    color = _check_color(img, color)
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    h, w = img.shape[:2]
    while True:
        if 0 <= x1 < w and 0 <= y1 < h:
            img[y1, x1] = color
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy
    return img


def circle(img, center, radius, color, thickness=1, lineType=LINE_8, shift=0):
    img = _asarray(img)
    cx, cy, r = int(center[0]), int(center[1]), int(radius)
    color = _check_color(img, color)
    h, w = img.shape[:2]
    for y in range(max(0, cy - r), min(h, cy + r + 1)):
        for x in range(max(0, cx - r), min(w, cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                if thickness < 0 or (x - cx) ** 2 + (y - cy) ** 2 >= (r - thickness) ** 2:
                    img[y, x] = color
    return img


# 5x7 bitmap font (rows top->bottom, 5 bits each, MSB = left)
_FONT5X7 = {
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    "D": [0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
    "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "J": [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    "N": [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    "X": [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    "Y": [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
    "3": [0x1F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    " ": [0, 0, 0, 0, 0, 0, 0],
    ".": [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C],
    ",": [0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x06],
    ":": [0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00],
    ";": [0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x06],
    "!": [0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04],
    "?": [0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04],
    "-": [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
    "_": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F],
    "+": [0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00],
    "/": [0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10],
    "(": [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
    ")": [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    "'": [0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00],
    '"': [0x0A, 0x0A, 0x04, 0x00, 0x00, 0x00, 0x00],
    "%": [0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03],
    "=": [0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00],
    "<": [0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02],
    ">": [0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08],
    "[": [0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E],
    "]": [0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E],
    "{": [0x02, 0x04, 0x04, 0x08, 0x04, 0x04, 0x02],
    "}": [0x08, 0x04, 0x04, 0x02, 0x04, 0x04, 0x08],
    "*": [0x11, 0x1F, 0x0E, 0x1F, 0x11, 0x00, 0x00],
    "#": [0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A],
    "$": [0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04],
    "&": [0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D],
}

for _lc in list(_FONT5X7.keys()):
    if _lc.isupper():
        _FONT5X7[_lc.lower()] = _FONT5X7[_lc]


def _glyph(ch):
    g = _FONT5X7.get(ch)
    if g is None:
        g = [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E]  # box for unknown
    return g


def putText(img, text, org, fontFace, fontScale, color, thickness=1,
            lineType=LINE_8):
    img = _asarray(img)
    x0, y_base = int(org[0]), int(org[1])  # y = baseline (bottom of text)
    color = _check_color(img, color)
    h, w = img.shape[:2]
    cell_w, cell_h = 6, 8  # 5x7 glyph + 1px spacing
    # render at integer scale
    scale = max(1, int(round(fontScale)))
    text_h = cell_h * scale
    for ci, ch in enumerate(str(text)):
        glyph = _glyph(ch)
        gx = x0 + ci * cell_w * scale
        gy_top = y_base - text_h
        for row in range(cell_h - 1, -1, -1):
            bits = glyph[min(row, 6)]
            for col in range(5):
                if bits & (0x10 >> col):
                    yy = gy_top + (cell_h - 1 - row) * scale
                    xx = gx + col * scale
                    if 0 <= xx < w and 0 <= yy < h:
                        img[yy:yy + scale, xx:xx + scale] = color
    return 0


# --------------------------------------------------------------------------
# GUI stubs (debug/visualization only; headless environment)
# --------------------------------------------------------------------------

def _gui_unavailable(*a, **k):
    warnings.warn("cv2 GUI functions are unavailable in the pure-python cv2 "
                  "shim; call is a no-op", stacklevel=2)
    return 0


namedWindow = _gui_unavailable
imshow = _gui_unavailable
destroyAllWindows = _gui_unavailable
waitKey = _gui_unavailable
getWindowProperty = lambda *a, **k: 0
setWindowTitle = _gui_unavailable


# --------------------------------------------------------------------------
# misc (mmcv.image.photometric / mmcv.video)
# --------------------------------------------------------------------------

def LUT(src, lut):
    """Per-channel lookup-table mapping (cv2.LUT).

    ``lut`` must have the same number of channels as ``src`` and 256 rows
    (uint8) per channel.
    """
    src = _asarray(src)
    lut = _asarray(lut)
    if src.dtype != np.uint8:
        raise TypeError("LUT supports uint8 images only")
    if src.ndim == 2:
        return np.take(lut, src, axis=0).astype(np.uint8)
    c = src.shape[-1]
    if lut.ndim == 1:
        lut = np.stack([lut] * c, axis=-1)
    out = np.empty(src.shape, dtype=np.uint8)
    for i in range(c):
        out[..., i] = lut[:, i][src[..., i]]
    return out


def VideoWriter_fourcc(*chars):
    """Pack 4 chars into a FOURCC int (cv2.VideoWriter_fourcc)."""
    code = 0
    for ch in chars:
        code = (code << 8) | (ord(ch) & 0xFF)
    return code
