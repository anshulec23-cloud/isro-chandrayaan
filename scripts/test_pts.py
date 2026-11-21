import urllib.request
import json

for pt in ['EDRNAC4', 'CDRNAC4', 'BDR']:
    url = f'https://oderest.rsl.wustl.edu/live2?query=product&target=moon&results=c&output=JSON&ihid=LRO&iid=LROC&pt={pt}&minlat=0.0&maxlat=10.0&westernlon=1.0&easternlon=5.0&loc=b'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode('utf-8-sig', errors='ignore')
            data = json.loads(raw)
            cnt = data.get('ODEResults', {}).get('QuerySummary', {}).get('TotalCount', 'N/A')
            status = data.get('ODEResults', {}).get('Status', '')
            print(f'PT: {pt} -> Status: {status}, TotalCount: {cnt}')
            if status == 'ERROR':
                print('  Error:', data.get('ODEResults', {}).get('Error'))
    except Exception as e:
        print(f'PT: {pt} -> Error: {e}')
