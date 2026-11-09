"""WS12 v2: score 15 printed items from versioned, scan-reviewed observations.

No historical extraction/scoring file is overwritten. Correctness means local
internal consistency, not optimality or independent agreement with a human coder.
Run: python3 scripts/score_ws12.py [--publish-data] [--dry-run]
"""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[1]
REVISION = REPO / 'revisions/WS12/20261109-v2'
FEATURES = {'enerji','energy','kcal','yağ','yag','fat','doymuş yağ','doymus yag','saturated fat','şeker','seker','sugar','protein','tuz','sodyum','sodium','salt'}
SCORES = {'correct':1.0,'incorrect':0.0,'partial':0.5,'blank':0.0}
MISSING = {'','(not_extracted)','unknown','n/a'}


def parse_threshold(value):
    """Normalize x OP cutpoint and cutpoint OP x (e.g. 2,5≤ means x≥2.5)."""
    if not isinstance(value,str) or value.strip().lower() in MISSING:
        return None
    s=value.strip().replace(',','.').replace('<=','≤').replace('>=','≥')
    number=r'([+-]?\d+(?:\.\d+)?)'
    prefix=re.fullmatch(r'([≤≥<>])\s*'+number+r'\s*(?:kcal|g|mg)?',s,re.I)
    suffix=re.fullmatch(number+r'\s*([≤≥<>])\s*(?:kcal|g|mg)?',s,re.I)
    if prefix:
        return prefix[1],Decimal(prefix[2])
    if suffix:
        return {'<':'>','>':'<','≤':'≥','≥':'≤'}[suffix[2]],Decimal(suffix[1])
    return None


def complementary(left,right):
    a,b=parse_threshold(left),parse_threshold(right)
    if a is None or b is None:
        return None
    return a[1]==b[1] and (a[0],b[0]) in {('≤','>'),('>','≤'),('<','≥'),('≥','<')}


def valid_counts(values):
    return isinstance(values,list) and len(values)==2 and all(type(v) is int and v>=0 for v in values) and sum(values)>0


def score_group(group):
    observations=group['items']; counts=group['counts']; decisions=group['decisions']
    rows={}
    def set_row(i,status,note):
        o=observations[str(i)]
        node={4:'left',5:'right',10:'ll',11:'lr',12:'rl',13:'rr'}.get(i)
        c=counts.get(node)
        observed_value=o['value']
        response_state=o['state']
        if observed_value is None and valid_counts(c):
            observed_value=f'Counts: recommended={c[0]}, not recommended={c[1]}; no explicit class selection established'
            response_state='observed'
        rows[i]={'item':f'WS12_P{i:02}','printed_item_id':str(i),'value':observed_value,'response_state':response_state,'count_evidence':c,'status':status,'score':SCORES.get(status),'max_score':None if status=='structural_na' else 1.0,'review':status=='unknown','note':note,'page':group['page'],'method':'deterministic_on_manually_reviewed_scan'}
    def feature(value):
        return isinstance(value,str) and value.strip().lower() in FEATURES
    def structure(node,label_item):
        if feature(observations[str(label_item)]['value']):return 'split'
        c=counts.get(node)
        if valid_counts(c) and min(c)==0:return 'stopped'
        return 'unknown'
    state={node:structure(node,i) for node,i in [('left',4),('right',5)]}
    def pair(a,b,activity='split'):
        if activity=='stopped':
            for i in [a,b]:set_row(i,'structural_na','Unused descendant of independently observed pure terminal node.')
            return
        if activity=='unknown':
            for i in [a,b]:set_row(i,'unknown','Branch activity cannot be established; absent threshold is not assumed blank or not applicable.')
            return
        x,y=observations[str(a)],observations[str(b)]
        if any(o.get('ambiguous') or o['state']=='missing' for o in [x,y]):
            for i in [a,b]:set_row(i,'unknown','Pair cannot be verified: ambiguous writing or unavailable extraction.')
            return
        comp=complementary(x['value'],y['value'])
        for i,o in [(a,x),(b,y)]:
            if o['state']=='blank':set_row(i,'blank','Confirmed physical blank on an active branch.')
            elif comp is None:set_row(i,'unknown','Numeric cutpoint/operator pair cannot be verified; no complement inferred.')
            else:set_row(i,'correct' if comp else 'incorrect','Same numeric cutpoint with complementary operators.' if comp else 'Branch pair has a gap, overlap, or different cutpoints. Pair consistency failure; neither isolated branch is claimed uniquely responsible.')
    def decision(i,node,activity):
        o=observations[str(i)];c=counts.get(node);d=decisions.get(node)
        if activity=='stopped':set_row(i,'structural_na','Unused descendant of independently observed pure terminal node.');return
        if activity=='unknown':set_row(i,'unknown','Whether this descendant is applicable is not established.');return
        if d is None:
            if valid_counts(c):set_row(i,'unknown','Class counts observed, but no unambiguous predicted class; counts are not a class decision.')
            elif o['state']=='blank':set_row(i,'blank','No class decision in the associated response region.')
            else:set_row(i,'unknown','Decision interpretation unavailable.')
        elif not valid_counts(c):set_row(i,'unknown','Class selection is observed; missing independent class counts prevent correctness verification.')
        elif c[0]==c[1]:set_row(i,'unknown','Tied counts require a documented tie rule.')
        else:
            agrees=(d=='recommended' and c[0]>c[1]) or (d=='not_recommended' and c[1]>c[0])
            set_row(i,'correct' if agrees else 'incorrect','Explicit class choice checked against independently observed majority/pure counts; dataset membership itself not verified.')
    o=observations['1']
    set_row(1,'blank' if o['state']=='blank' else 'unknown' if o.get('ambiguous') or o['state']=='missing' or o['value'] is None or str(o['value']).strip().lower() in MISSING else 'correct' if feature(o['value']) else 'incorrect','Food feature vocabulary check; optimal feature not established.')
    pair(2,3)
    for node,i in [('left',4),('right',5)]:
        if feature(observations[str(i)]['value']):set_row(i,'correct','Next food feature named; threshold and terminal decisions checked separately.')
        elif state[node]=='stopped' and node not in decisions:set_row(i,'structural_na','Pure node counts establish that no next split is needed; explicit class choice not inferred.')
        else:decision(i,node,'split')
    pair(6,7,state['left']);pair(8,9,state['right'])
    for node,items in [('left',[(10,'ll'),(11,'lr')]),('right',[(12,'rl'),(13,'rr')])]:
        for i,leaf in items:decision(i,leaf,state[node])
    active=[]; complete=True
    for node,children in [('left',['ll','lr']),('right',['rl','rr'])]:
        if state[node]=='stopped':active.append(node)
        elif state[node]=='split':active.extend(children)
        else:complete=False
    expected=0
    for node in active:
        c=counts.get(node);d=decisions.get(node)
        if not valid_counts(c) or d not in {'recommended','not_recommended'}:complete=False
        else:expected+=c[1] if d=='recommended' else c[0]
    value=observations['14']['value']
    if observations['14']['state']=='blank':set_row(14,'blank','Training-error field physically blank.')
    elif type(value) is not int or value<0:set_row(14,'unknown','Nonnegative integer could not be verified.')
    elif not complete:set_row(14,'unknown','Recorded value retained; actual class decisions/counts at every active terminal node are required.')
    else:set_row(14,'correct' if value==expected else 'incorrect',f'Reported training errors={value}; opposite-class counts under actual terminal predictions imply {expected}.')
    set_row(15,'blank' if observations['15']['state']=='blank' else 'unknown','Test-error field physically blank.' if observations['15']['state']=='blank' else 'Recorded number only; independent test cards/predictions unavailable, so correctness is unverified.')
    diagnostics=[]
    for node,children in [('left',['ll','lr']),('right',['rl','rr'])]:
        if state[node]!='split':continue
        values=[counts.get(n) for n in [node]+children]
        if all(valid_counts(v) for v in values):
            ok=all(values[0][k]==values[1][k]+values[2][k] for k in [0,1])
            diagnostics.append({'node':node,'status':'consistent' if ok else 'inconsistent','note':'Independently observed parent equals sum of child counts per class.'})
        else:diagnostics.append({'node':node,'status':'unknown','note':'Independent parent/child counts missing; no circular imputation.'})
    result=[rows[i] for i in range(1,16)]
    tallies=dict(Counter(r['status'] for r in result))
    known=[r for r in result if r['status'] in SCORES]
    unknown=tallies.get('unknown',0)
    return {'page':group['page'],'students':group['students'],'items':result,'status_counts':tallies,'resolved_count':len(known),'applicable_count':15-tallies.get('structural_na',0),'verified_subtotal':sum(r['score'] for r in known),'total_score':None if unknown else sum(r['score'] for r in known),'note':group['note'],'count_diagnostics':diagnostics}


def build_revision():
    obs=json.loads((REVISION/'observations.json').read_text())
    assert hashlib.sha256((REPO/obs['source_pdf']).read_bytes()).hexdigest()==obs['source_sha256'],'Scan changed; repeat visual review.'
    groups=[score_group(g) for g in obs['groups']]
    students=[s for g in groups for s in g['students']]
    assert len(students)==len(set(students))==13 and len(groups)==7
    assert all(len(g['items'])==15 for g in groups)
    rub=json.loads((REPO/'rubrics/WS12_rubric.json').read_text())
    schema=json.loads((REPO/'worksheets/WS12/extraction_schema.json').read_text())
    return {'version':obs['version'],'cohort':2026,'method':obs['method'],'source_pdf':'downloads/completed/WS12.pdf','source_sha256':obs['source_sha256'],'groups':groups,'absent':obs['absent'],'rubric':rub,'fields':schema['fields'],'historical_scores':'Preserved in students/*/WS12/scoring.json; superseded in the published WS12 view.','limitations':['This is a revised deterministic assessment using manually reviewed extraction, not independent AI performance.','WS6-to-WS12 group-tree fidelity and optimal threshold correctness are not established.','Test-error values are recorded but cannot be verified without test cards.','One shared sheet per group;13 student records correspond to7 independent physical submissions.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-data',action='store_true',help='Write only versioned site review data; no historical score edits')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    result=build_revision()
    if not args.dry_run:
        (REVISION/'scoring.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        if args.publish_data:
            dst=REPO/'mmla_explorer/site/data/ws12_review.js'
            dst.write_text('window.WS12_REVIEW='+json.dumps(result,ensure_ascii=False,separators=(',',':'))+';\n')
            download=REPO/'mmla_explorer/site/downloads/ws12_review'
            download.mkdir(exist_ok=True)
            for name,data in [('scoring.json',result),('rubric.json',result['rubric']),('observations.json',json.loads((REVISION/'observations.json').read_text()))]:
                (download/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    for g in result['groups']:print(' / '.join(g['students']),g['status_counts'])
    print('No historical extraction/scoring file modified.')


if __name__=='__main__':main()
