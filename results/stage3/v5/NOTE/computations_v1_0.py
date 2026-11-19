"""Computation 1 (brief-v1.0 s2.1): acted on and missed, serious + material plants (S3 + S2, reader A's class),
plants weighted equally. Each class figure in joins-v1.json is a plant-weighted mean over the class's RM plants,
so the 42-plant figure is the n-weighted mean of the S3 and S2 class figures (checked: the same combination over
all three classes reproduces the 48-plant 'all' figure). No interval: the bootstrap needs per-run files behind the barrier."""
import json, hashlib, sys
import pathlib
p = str(pathlib.Path(__file__).resolve().parents[1] / 'P1' / 'joins-v1.json')
print('joins-v1.json sha256', hashlib.sha256(open(p,'rb').read()).hexdigest()[:8])
d = json.load(open(p))
cc = d['consequence_classes']['class_a']
cols = ['raw','positive_upper','positive_lower','negative_unclear_not_acting','negative_unclear_acting','both_lower_unclear_not_acting','both_upper_unclear_acting']
print(json.dumps({k: (cc['S3'][k]['n_RM'] if 'n_RM' in cc['S3'][k] else None) for k in cols}))
for col in cols:
    n = {c: cc[c][col]['n_RM'] for c in ('S1','S2','S3')}
    s = {c: cc[c][col]['S']['point'] for c in ('S1','S2','S3')}
    sm = (n['S3']*s['S3'] + n['S2']*s['S2'])/(n['S3']+n['S2'])
    allc = sum(n[c]*s[c] for c in n)/sum(n.values())
    print(f"{col:32s} n={n} S3={s['S3']:.6f} S2={s['S2']:.6f}  serious+material={sm:.6f}  check all={allc:.6f} record all={d['all'][col]['S']['point']:.6f}")
