import json,sys
book,pno=sys.argv[1],int(sys.argv[2]); lo=float(sys.argv[3]) if len(sys.argv)>3 else 0; hi=float(sys.argv[4]) if len(sys.argv)>4 else 9999
col=sys.argv[5] if len(sys.argv)>5 else None
S='/home/shankar/pup/ghatnachakra/mcq-portal/work/lines/'+book+'.json'
d={r[0]:r for r in json.load(open(S))}
for l in sorted(d[pno][3],key=lambda l:(l['col'],l['top'])):
    if lo<=l['top']<=hi and (col is None or int(col)==l['col']): print(l['col'],'B%.1f'%l['bold'],'[]' if l['boxed'] else '  ',l['x0'],l['top'],repr(l['text'][:100]))
