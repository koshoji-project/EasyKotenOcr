"""EasyKotenOCR インストーラー補助（モデルダウンロード）。

venv 構築後の venv Python（3.15）での実行を前提とする。
URL・保存先・SHA256 はすべて manifest.json から読む（第1引数）。

仕様 INSTALLER_SPEC_v2.1.md §5.7:
- リトライ3回（指数バックオフ）、Resume（Range ヘッダー）、既存ファイルは
  SHA256 一致でスキップ（sha256 未設定ならサイズ下限のみ検証し警告）
- NDL 側の仕様変更検出: HTML / 想定外サイズが返ったら失敗
- ZIP は展開する（展開済みマーカーで冪等）

使い方:
  python installer.py <manifest.json> <インストール先ルート>
終了コード: 0=成功 / 1=失敗
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

UA = "EasyKotenInstaller/2.1"
CHUNK = 1024 * 256
RETRIES = 3
HTML_SNIFF = (b"<!DOCTYPE", b"<html", b"<HTML")


def log(msg):
    print(msg, flush=True)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def looks_like_html(path):
    with open(path, "rb") as f:
        head = f.read(64).lstrip()
    return any(head.startswith(m) for m in HTML_SNIFF)


def download(url, dest, min_bytes):
    """Resume 対応ダウンロード。戻り値: 完了なら True"""
    part = dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    pos = os.path.getsize(part) if os.path.exists(part) else 0
    mode = "ab" if pos else "wb"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if pos:
        req.add_header("Range", f"bytes={pos}-")
        log(f"  続き ({pos:,} バイト目) から再開します")
    with urllib.request.urlopen(req, timeout=120) as resp:
        if pos and resp.status != 206:
            log("  サーバーが Range を無視したため最初からダウンロードします")
            pos, mode = 0, "wb"
        total = pos + int(resp.headers.get("content-length", 0) or 0)
        with open(part, mode) as f:
            done = pos
            last_report = 0
            while True:
                blk = resp.read(CHUNK)
                if not blk:
                    break
                f.write(blk)
                done += len(blk)
                if done - last_report >= 10 * 1024 * 1024:
                    last_report = done
                    if total:
                        log(f"  {done / 1048576:.0f} MB / {total / 1048576:.0f} MB"
                            f" ({done * 100 // total}%)")
                    else:
                        log(f"  {done / 1048576:.0f} MB ダウンロード済み")
    if total and done < total:
        raise OSError(f"ダウンロードが途中で終わりました ({done}/{total})")
    os.replace(part, dest)
    return True


def fetch_one(model, root):
    dest = os.path.join(root, *model["dest"].split("/"))
    sha_expect = (model.get("sha256") or "").strip().lower()
    label = model.get("label", model["url"])
    min_bytes = int(model.get("min_bytes", 0))

    # 既存ファイルのスキップ判定
    if os.path.exists(dest):
        if sha_expect:
            if sha256_of(dest) == sha_expect:
                log(f"  済み: {label}（ハッシュ一致のためスキップ）")
                return True
            log(f"  既存ファイルのハッシュ不一致。再ダウンロードします: {label}")
            os.remove(dest)
        elif min_bytes and os.path.getsize(dest) >= min_bytes:
            log(f"  済み: {label}（sha256 未設定・サイズ下限を満たすためスキップ）")
            return True

    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            log(f"  ダウンロード中（{attempt}/{RETRIES}回目）: {label}")
            download(model["url"], dest, min_bytes)
            # 中身の健全性チェック（HTMLエラーページ混入・サイズ不足）
            if looks_like_html(dest):
                os.remove(dest)
                raise OSError("HTML が返されました（リンク切れ・仕様変更の可能性）")
            size = os.path.getsize(dest)
            if min_bytes and size < min_bytes:
                os.remove(dest)
                raise OSError(f"サイズが想定より小さすぎます（{size} バイト）")
            if sha_expect:
                actual = sha256_of(dest)
                if actual != sha_expect:
                    os.remove(dest)
                    raise OSError(f"SHA256 不一致: {actual}")
            elif not sha_expect:
                log("  注意: manifest.json に sha256 が未設定のためハッシュ検証は省略")
            log(f"  完了: {label}（{size:,} バイト）")
            last_err = None
            break
        except Exception as e:  # noqa: BLE001 — リトライ対象として広く捕捉
            last_err = e
            log(f"  失敗: {e}")
            if attempt < RETRIES:
                time.sleep(5 * attempt)

    if last_err is not None:
        log(f"  エラー: {label} のダウンロードに失敗し続けます")
        return False

    # ZIP 展開（マーカーで冪等）
    extract_to = model.get("extract_to")
    if extract_to:
        target = os.path.join(root, *extract_to.split("/"))
        marker = os.path.join(target, ".easykoten_extracted")
        if os.path.exists(marker):
            log("  展開済みためスキップ")
        else:
            log(f"  展開中: {target}")
            with zipfile.ZipFile(dest) as zf:  # CRC もここで検証される
                zf.extractall(target)
            with open(marker, "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    return True


def main():
    if len(sys.argv) != 3:
        print("usage: installer.py <manifest.json> <install-root>")
        return 1
    manifest_path, root = sys.argv[1], sys.argv[2]
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    models = manifest.get("models", [])
    if not models:
        print("manifest.json に models が見つかりません")
        return 1
    ok = True
    for m in models:
        if not fetch_one(m, root):
            ok = False
    if ok:
        log("MODEL DOWNLOAD OK")
        return 0
    log("MODEL DOWNLOAD FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
