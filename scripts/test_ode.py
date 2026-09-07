import urllib.request
import json
import xml.etree.ElementTree as ET

# Query ODE for instruments on Moon
url = 'http://oderest.rsl.wustl.edu/live?target=moon&query=instrument&output=JSON'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('utf-8-sig')
        data = json.loads(content)
        instruments = data.get('ODEResults', {}).get('Instruments', {}).get('Instrument', [])
        print(f'Total instruments: {len(instruments)}')
        for inst in instruments:
            name = inst.get('InstrumentName', '')
            iid = inst.get('InstrumentId', '')
            mission = inst.get('MissionName', '')
            mid = inst.get('MissionId', '')
            if 'LROC' in iid or 'LRO' in mid or 'SELENE' in mid or 'KAGUYA' in mid or 'TC' in iid:
                print(f'{mid} | {mission} | {iid} | {name}')
except Exception as e:
    print('Error:', e)
