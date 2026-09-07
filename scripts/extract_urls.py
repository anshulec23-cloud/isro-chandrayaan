with open('scripts/ode_response.xml', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
examples = re.findall(r'href=[\'"]([^\'"]*query=[^\'"]*)[\'"]', text)
print(f'Found query links: {len(examples)}')
for e in examples[:15]:
    print(e)
