import urllib.request

urls = [
    ('LROC XML', 'https://pds.lroc.im-ldi.com/data/LRO-L-LROC-3-CDR-V1.0/LROLRC_1053A/DATA/ESM4/2022270/NAC/M1418935915LC.xml'),
    ('LROC IMG', 'https://pds.lroc.im-ldi.com/data/LRO-L-LROC-3-CDR-V1.0/LROLRC_1053A/DATA/ESM4/2022270/NAC/M1418935915LC.IMG'),
    ('SELENE LBL', 'https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-ortho-map-v2.0/lon141/data/TCO_MAP_02_S06E141S09E144SC.lbl'),
    ('SELENE IMG', 'https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-ortho-map-v2.0/lon141/data/TCO_MAP_02_S06E141S09E144SC.img'),
]

for name, url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            code = r.getcode()
            length = r.headers.get('Content-Length')
            ctype = r.headers.get('Content-Type')
            mb = f'{int(length)/1e6:.2f} MB' if length else 'Unknown'
            print(f'{name}: HTTP {code} | Length: {length} ({mb}) | Type: {ctype}')
    except Exception as e:
        print(f'{name}: Error: {e}')
