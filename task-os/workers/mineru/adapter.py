#!/usr/bin/env python3
"""MinerU 单文件 PDF→MD 适配器。

Usage: python3 adapter.py <input.pdf> <output.md> [ch|en]

环境变量: MINERU_API_KEY
"""

import os
import sys
import json
import time
import zipfile
import shutil
import urllib.request
import urllib.error
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: adapter.py <input.pdf> <output.md> [ch|en]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_md = sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else "ch"

    api_key = os.environ.get("MINERU_API_KEY", "")
    if not api_key:
        print("ERROR: MINERU_API_KEY not set")
        sys.exit(1)

    base_url = "https://mineru.net/api/v4"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    def api_request(endpoint, method="GET", data=None):
        url = f"{base_url}{endpoint}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        if result.get("code") != 0:
            print(f"API error: {result}")
            sys.exit(1)
        return result["data"]

    def upload_file(upload_url, filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        req = urllib.request.Request(upload_url, data=data, method="PUT")
        req.add_header("Content-Type", "")
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status

    filename = Path(input_pdf).name
    stem = Path(input_pdf).stem
    data_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in stem)[:128]

    # Step 1: Request upload URL
    print(f"[MinerU] Requesting upload URL for {filename}...")
    req_data = {
        "files": [{"name": filename, "data_id": data_id}],
        "model_version": "vlm",
        "enable_formula": True,
        "enable_table": True,
        "language": language,
    }
    result = api_request("/file-urls/batch", "POST", req_data)
    upload_url = result["file_urls"][0]
    batch_id = result.get("batch_id", "")
    print(f"[MinerU] batch_id={batch_id}")

    # Step 2: Upload
    print(f"[MinerU] Uploading {filename}...")
    upload_file(upload_url, input_pdf)
    print(f"[MinerU] Upload done.")

    # Step 3: Poll
    print(f"[MinerU] Waiting for processing...")
    while True:
        time.sleep(15)
        try:
            status = api_request(f"/extract-results/batch/{batch_id}")
        except Exception as e:
            print(f"[MinerU] Poll error: {e}, retrying...")
            time.sleep(15)
            continue

        for item in status.get("extract_result", []):
            s = item.get("state", "unknown")
            if s == "done":
                zip_url = item.get("full_zip_url")
                if zip_url:
                    print(f"[MinerU] Processing done.")
                    # Step 4: Download and extract
                    tmp_dir = Path(output_md).parent / f".mineru_tmp_{data_id}"
                    tmp_dir.mkdir(exist_ok=True)
                    zip_path = tmp_dir / "result.zip"
                    urllib.request.urlretrieve(zip_url, str(zip_path))

                    with zipfile.ZipFile(str(zip_path), "r") as z:
                        z.extractall(str(tmp_dir))

                    # Find .md file
                    md_files = list(tmp_dir.rglob("*.md"))
                    if md_files:
                        # Merge if multiple
                        Path(output_md).parent.mkdir(parents=True, exist_ok=True)
                        with open(output_md, "w", encoding="utf-8") as out:
                            for md in sorted(md_files):
                                with open(md, "r", encoding="utf-8") as f:
                                    out.write(f.read())
                                out.write("\n\n")
                        size_kb = Path(output_md).stat().st_size / 1024
                        print(f"[MinerU] Output: {output_md} ({size_kb:.1f}KB)")
                    else:
                        print(f"[MinerU] ERROR: No .md files in ZIP")
                        sys.exit(1)

                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    return
            elif s == "failed":
                print(f"[MinerU] Processing failed: {item.get('err_msg', 'unknown')}")
                sys.exit(1)

        running = sum(1 for i in status.get("extract_result", []) if i.get("state") == "running")
        if running > 0:
            for item in status.get("extract_result", []):
                if item["state"] == "running" and item.get("extract_progress"):
                    p = item["extract_progress"]
                    print(f"[MinerU] Progress: {p.get('extracted_pages', 0)}/{p.get('total_pages', 0)} pages")
                    break


if __name__ == "__main__":
    main()
