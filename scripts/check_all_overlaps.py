import urllib.request
import json

def search(ihid, iid, pt, minlat, maxlat, wlon, elon, label):
    url = (
        f'https://oderest.rsl.wustl.edu/live2/?query=products&target=moon&results=m&output=JSON'
        f'&ihid={ihid}&iid={iid}&pt={pt}'
        f'&minlat={minlat}&maxlat={maxlat}&westernlon={wlon}&easternlon={elon}'
        f'&loc=b&limit=5'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f'=== Querying {label} ({ihid}/{iid}/{pt}) ===')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8-sig', errors='ignore'))
            prods = data.get('ODEResults', {}).get('Products', {}).get('Product', [])
            if isinstance(prods, dict): prods = [prods]
            print(f'Found {len(prods)} products for {label}')
            for p in prods[:3]:
                print('  Name:', p.get('Product_name'))
                minl, maxl = p.get('Minimum_latitude'), p.get('Maximum_latitude')
                w, e = p.get('Westernmost_longitude'), p.get('Easternmost_longitude')
                print(f'  Lat: [{minl}, {maxl}], Lon: [{w}, {e}]')
                print('  Res:', p.get('Map_resolution'), 'm/px')
                print('  LabelURL:', p.get('LabelURL'))
    except Exception as e:
        print(f'Error for {label}: {e}')

# 1. LRO CDRNAC4 over OHRC South Pole [-85.48, -84.66], [23.41, 28.33]
search('LRO', 'LROC', 'CDRNAC4', -85.48, -84.66, 23.41, 28.33, 'LROC CDR over OHRC South Pole')

# 2. LRO CDRNAC4 over TMC Equatorial [-29.51, -3.62], [140.78, 142.71] (test a 2x2 deg sub-window first to be fast)
search('LRO', 'LROC', 'CDRNAC4', -10.0, -8.0, 141.0, 142.5, 'LROC CDR over TMC Equatorial (sub-window)')

# 3. SELENE TC (TCORT) over TMC Equatorial
search('SLN', 'TC', 'TCORT', -10.0, -8.0, 141.0, 142.5, 'SELENE TCORT over TMC Equatorial (sub-window)')
