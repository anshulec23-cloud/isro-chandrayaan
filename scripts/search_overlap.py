import urllib.request
import json

def query_ode(target, ihid, iid, pt, minlat, maxlat, westernlon, easternlon, limit=5):
    # results=m returns metadata; results=c returns count; results=m&limit=5
    url = (
        f'https://oderest.rsl.wustl.edu/live2?target={target}&query=product&output=JSON'
        f'&ihid={ihid}&iid={iid}&pt={pt}'
        f'&minlat={minlat}&maxlat={maxlat}&westernlon={westernlon}&easternlon={easternlon}'
        f'&results=m&limit={limit}'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8-sig', errors='ignore'))
            ode_res = data.get('ODEResults', {})
            count = ode_res.get('QuerySummary', {}).get('TotalCount', 0)
            products = ode_res.get('Products', {}).get('Product', [])
            if isinstance(products, dict):
                products = [products]
            return count, products
    except Exception as e:
        print(f'Error querying {ihid}/{iid}/{pt}: {e}')
        return 0, []

print('=== 1. Checking LRO NAC over OHRC South Pole Footprint ===')
# OHRC: Lat [-85.48, -84.66], Lon [23.41, 28.33]
c, prods = query_ode('moon', 'LRO', 'LROC', 'CDRNAC4', -85.48, -84.66, 23.41, 28.33, limit=3)
print(f'LRO NAC (CDRNAC4) count over OHRC South Pole: {c}')
for p in prods:
    print('  ID:', p.get('pdsid'), '| Center:', p.get('CenterLatitude'), p.get('CenterLongitude'), '| URL:', p.get('External_URL'))

print('\n=== 2. Checking LRO NAC over TMC Equatorial Footprint ===')
# TMC: Lat [-29.51, -3.62], Lon [140.78, 142.71]
c2, prods2 = query_ode('moon', 'LRO', 'LROC', 'CDRNAC4', -29.51, -3.62, 140.78, 142.71, limit=3)
print(f'LRO NAC (CDRNAC4) count over TMC swath: {c2}')
for p in prods2:
    print('  ID:', p.get('pdsid'), '| Center:', p.get('CenterLatitude'), p.get('CenterLongitude'), '| URL:', p.get('External_URL'))

print('\n=== 3. Checking SELENE TC (TCORT) over TMC Equatorial Footprint ===')
c3, prods3 = query_ode('moon', 'SLN', 'TC', 'TCORT', -29.51, -3.62, 140.78, 142.71, limit=3)
print(f'SELENE TC (TCORT) count over TMC swath: {c3}')
for p in prods3:
    print('  ID:', p.get('pdsid'), '| Center:', p.get('CenterLatitude'), p.get('CenterLongitude'), '| URL:', p.get('External_URL'))
