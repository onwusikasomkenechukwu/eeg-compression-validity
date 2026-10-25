"""Resumable parallel download of PhysioNet and OpenNeuro datasets from their open S3 buckets.

Usage: python scripts/download_data.py chbmit|siena|seizeit2 [--workers 8]
Files already on disk with the right size are skipped, so re-running resumes.
"""
import argparse
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

PHYSIONET = "https://physionet-open.s3.amazonaws.com"
OPENNEURO = "https://s3.amazonaws.com/openneuro.org"
DATASETS = {
    "chbmit": (PHYSIONET, "chbmit/1.0.0/"),
    "siena": (PHYSIONET, "siena-scalp-eeg/1.0.0/"),
    "seizeit2": (OPENNEURO, "ds005873/"),
}
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def list_objects(bucket, prefix):
    token = None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        with urllib.request.urlopen(f"{bucket}/?{urllib.parse.urlencode(q)}") as r:
            tree = ET.parse(r).getroot()
        for c in tree.findall("s3:Contents", NS):
            yield c.find("s3:Key", NS).text, int(c.find("s3:Size", NS).text)
        if tree.find("s3:IsTruncated", NS).text != "true":
            return
        token = tree.find("s3:NextContinuationToken", NS).text


def fetch(bucket, key, size, dest, retries=30):
    if os.path.exists(dest) and os.path.getsize(dest) == size:
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    for attempt in range(retries):
        try:
            done = os.path.getsize(tmp) if os.path.exists(tmp) else 0
            req = urllib.request.Request(f"{bucket}/{urllib.parse.quote(key)}")
            if done:
                req.add_header("Range", f"bytes={done}-")
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "ab" if done else "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            if os.path.getsize(tmp) != size:
                raise IOError(f"size mismatch {os.path.getsize(tmp)} != {size}")
            os.replace(tmp, dest)
            return size
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"{key}: {e}")
            # Cap the backoff at a minute so a dropped connection is waited out (~25 min total).
            time.sleep(min(2 ** attempt, 60))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", choices=DATASETS)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    bucket, prefix = DATASETS[args.dataset]
    out = os.path.join(ROOT, args.dataset)
    objs = [(k, s) for k, s in list_objects(bucket, prefix) if not k.endswith("/")]
    total = sum(s for _, s in objs)
    print(f"{args.dataset}: {len(objs)} files, {total / 1e9:.1f} GB -> {os.path.abspath(out)}", flush=True)

    got, failed, t0 = 0, [], time.time()
    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(fetch, bucket, k, s, os.path.join(out, k[len(prefix):])): k for k, s in objs}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                got += fut.result()
            except Exception as e:
                failed.append(str(e))
            if i % 25 == 0 or i == len(objs):
                rate = got / max(time.time() - t0, 1) / 1e6
                print(f"  {i}/{len(objs)} files, {got / 1e9:.1f} GB new, {rate:.1f} MB/s", flush=True)

    for f in failed:
        print("FAILED", f)
    print("done" if not failed else f"{len(failed)} failed; re-run to resume", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
