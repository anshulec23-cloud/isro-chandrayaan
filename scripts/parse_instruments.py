import urllib.request
import xml.etree.ElementTree as ET

url = 'http://oderest.rsl.wustl.edu/live?target=moon&query=instrument'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = resp.read().decode('utf-8-sig', errors='ignore')
    root = ET.fromstring(data)
    for inst in root.iter('Instrument'):
        iid = inst.findtext('InstrumentId', '')
        name = inst.findtext('InstrumentName', '')
        mid = inst.findtext('MissionId', '')
        mname = inst.findtext('MissionName', '')
        if any(k in (iid + mid + name + mname).upper() for k in ['LROC', 'NAC', 'SELENE', 'KAGUYA', 'TC']):
            print(f"{mid} | {iid} | {name}")
