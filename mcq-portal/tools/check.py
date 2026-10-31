import json,sys
from itertools import groupby
qs=json.load(open(sys.argv[1]))['questions']
for ch,g in groupby(qs,key=lambda q:q['chapter']):
    g=list(g); nums=[q['num'] for q in g]
    miss=sorted(set(range(1,nums[-1]+1))-set(nums))
    if miss or nums[-1]!=len(g): print('SEQ',ch,len(g),nums[-1],'p',g[0]['page'],'missing',miss[:12],'...' if len(miss)>12 else '')
for q in qs:
    iss=[i for i in q['issues'] if not i.startswith('ans_special') and not i.startswith('ans_tail')]
    if iss: print(q['chapter'],q['num'],q['page'],iss)
