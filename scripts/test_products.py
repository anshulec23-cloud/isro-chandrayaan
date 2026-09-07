import urllib.request
import json

# Test with query=products and loc=b / loc=c
url = 'https://oderest.rsl.wustl.edu/live2?query=products&target=moon&results=c&output=JSON&ihid=LRO&iid=LROC&minlat=0.0&maxlat=10.0&westernlon=1.0&easternlon=5.0&loc=b'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode('utf-8-sig', errors='ignore')
        print(raw[:500])
except Exception as e:
    print('Error:', e)
