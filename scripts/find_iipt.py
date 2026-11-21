import json

with open('scripts/moon_iipt.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

iipt = data.get('ODEResults', {}).get('IIPTSets', {}).get('IIPTSet', [])
print('Total IIPTSets:', len(iipt))
for item in iipt:
    ihid = item.get('IHID', '')
    iid = item.get('IID', '')
    pt = item.get('PT', '')
    ptname = item.get('PTDescription', '')
    if any(k in (ihid + iid + pt + ptname).upper() for k in ['LROC', 'NAC', 'SELENE', 'KAGUYA', 'TC']):
        print(f'{ihid} | {iid} | {pt} | {ptname}')
