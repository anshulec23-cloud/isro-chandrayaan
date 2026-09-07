import json

with open('scripts/moon_iipt.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find instruments/product types related to LROC, NAC, SELENE, Kaguya, TC
results = data.get('ODEResults', {})
print('Keys in ODEResults:', list(results.keys()))

# Look for instruments
insts = results.get('Instruments', {}).get('Instrument', [])
if not insts and isinstance(results.get('Instrument'), list):
    insts = results.get('Instrument')

print(f'Total elements: {len(insts)}')
for item in insts:
    text = json.dumps(item)
    if any(k in text.upper() for k in ['LROC', 'NAC', 'SELENE', 'KAGUYA', 'TC', 'TERRAIN']):
        print(item)
