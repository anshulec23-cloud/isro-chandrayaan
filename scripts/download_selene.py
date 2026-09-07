import urllib.request
import os
import time

url = 'https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-ortho-map-v2.0/lon141/data/TCO_MAP_02_S06E141S09E144SC.img'
dest = 'data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.img'

print(f'Starting download from {url} to {dest}')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
t0 = time.time()
downloaded = 0
last_report = 0

with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
    total_len = int(r.headers.get('Content-Length', 0))
    print(f'Total size: {total_len / 1e6:.2f} MB')
    while True:
        chunk = r.read(1024 * 1024) # 1 MB
        if not chunk:
            break
        f.write(chunk)
        downloaded += len(chunk)
        if downloaded - last_report >= 25 * 1024 * 1024 or downloaded == total_len:
            elapsed = time.time() - t0
            rate = (downloaded / 1e6) / elapsed if elapsed > 0 else 0
            print(f'Progress: {downloaded / 1e6:.1f} / {total_len / 1e6:.1f} MB ({downloaded / total_len * 100:.1f}%) at {rate:.2f} MB/s')
            last_report = downloaded

print('Download complete!')
