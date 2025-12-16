import json, pprint, sys
sys.path.insert(0, 'src')
from validators import run_all_checks
p = 'parser/results/header_numbers.json'
with open(p, encoding='utf-8') as f:
    data = json.load(f)
if isinstance(data, list):
    data = {'sections': data, 'file': p}
out = run_all_checks(data)
pp = pprint.PrettyPrinter(indent=2, width=120)
pp.pprint(out)
