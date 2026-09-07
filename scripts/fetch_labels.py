import urllib.request

# Download labels
lroc_url = 'https://pds.lroc.im-ldi.com/data/LRO-L-LROC-3-CDR-V1.0/LROLRC_1053A/DATA/ESM4/2022270/NAC/M1418935915LC.xml'
selene_url = 'https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-ortho-map-v2.0/lon141/data/TCO_MAP_02_S06E141S09E144SC.lbl'

req_l = urllib.request.Request(lroc_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_l, timeout=15) as r:
    with open('data/M1418935915LC.xml', 'wb') as f:
        f.write(r.read())
print('Downloaded data/M1418935915LC.xml')

req_s = urllib.request.Request(selene_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_s, timeout=15) as r:
    with open('data/TCO_MAP_02_S06E141S09E144SC.lbl', 'wb') as f:
        f.write(r.read())
print('Downloaded data/TCO_MAP_02_S06E141S09E144SC.lbl')
