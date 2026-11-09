"""Publish explicitly adjudicated stopping exceptions without rewriting source scores."""
import argparse,collections,copy,hashlib,json
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
REV=ROOT/'revisions/structural_stopping_20261109'

def dumps(x):return json.dumps(x,ensure_ascii=False,indent=2)+'\n'
def build(human):
    book=load_workbook(human,data_only=True,read_only=True);s=book['Copy of Worksheet Analiz'];header=next(s.values)
    names={str(v):i+1 for i,v in enumerate(header) if v in ('Zara','Marcus','Marco')};assert set(names)=={'Zara','Marcus','Marco'}
    cases=[{'worksheet':'WS6','students':['Zara'],'root_cell':'inner_left','root_prior_status':'incorrect','root_blank_evidence':'Published extracted response (bos)','node':'left','cells':{'inner_left':[4],'threshold_left':[5,6],'terminal_left':[7,8]},'source_rows':{4:54,5:55,6:56,7:57,8:58}}, {'worksheet':'WS12','students':['Marcus','Marco'],'root_cell':'WS12_P04','root_prior_status':'blank','root_blank_evidence':'Published status blank, response_state blank','node':'left','cells':{f'WS12_P{n:02}':[n] for n in [4,6,7,10,11]},'source_rows':{4:82,6:84,7:85,10:88,11:89}}]
    for case in cases:
        evidence={}
        for student in case['students']:
            evidence[student]={}
            for ns in case['cells'].values():
                for n in ns:
                    cell=s.cell(case['source_rows'][n],names[student]);assert str(cell.value).strip()=='|',(student,n,cell.value)
                    evidence[student][str(n)]=cell.coordinate
        case['human_cells']=evidence
    book.close()
    data={'version':'20261109-stopping-v1','human_reference_filename':Path(human).name,'human_reference_sha256':hashlib.sha256(Path(human).read_bytes()).hexdigest(),'sheet':'Copy of Worksheet Analiz','authorization':'User confirmed: | entries read as blank are accepted as valid stopping, and visibly marked separately.','meaning':'| = accepted correct stopping action / structurally not applicable, not a substantive answered-item correct label.','decision_origin':'researcher_confirmed_applicability; informed by human reference, not a blind new machine prediction','scope':'Only the two documented root stopping decisions below and their unused descendants. Other null/unknown values are not reclassified.','cases':cases,'ws6_display_overrides':{}}
    base=json.loads((ROOT/'revisions/WS12/20261109-v2/scoring.json').read_text());merged=copy.deepcopy(base);merged['version']='20261109-v3-stopping'
    for case in cases:
        reason='| Accepted correct stopping action after researcher applicability review. Human reference informed this exception; raw response and prior judgment retained. Unused descendants require no answer.'
        if case['worksheet']=='WS6':
            for student in case['students']:
                data['ws6_display_overrides'][student]={key:{'status':'structural_na','accepted_as_correct_action':True,'decision_origin':data['decision_origin'],'printed_items':ns,'excel_cells':[case['human_cells'][student][str(n)] for n in ns],'is_root_exception':key==case['root_cell'],'reason':reason} for key,ns in case['cells'].items()}
        else:
            group=next(g for g in merged['groups'] if set(g['students'])==set(case['students']))
            for item in group['items']:
                if item['item'] not in case['cells']:continue
                is_root=item['item']==case['root_cell']
                assert item['status']==('blank' if is_root else 'unknown')
                if is_root:assert item['response_state']=='blank' and item['value'] is None
                item.update({'previous_status':item['status'],'previous_note':item['note'],'status':'structural_na','score':None,'max_score':None,'review':False,'accepted_as_correct_action':True,'researcher_override':True,'override_source':'stopping_review/policy.json','decision_origin':data['decision_origin'],'method':'researcher_confirmed_applicability','override_excel_cells':[case['human_cells'][student][item['printed_item_id']] for student in case['students']],'note':reason})
            group['status_counts']=dict(collections.Counter(i['status'] for i in group['items']));group['applicable_count']=15-group['status_counts'].get('structural_na',0);group['resolved_count']=sum(i['score'] is not None for i in group['items']);group['note']+=' Left stopping/unused descendants accepted under documented researcher applicability review.'
    merged['applicability_policy_version']=data['version'];merged['base_review_version']=base['version'];merged['method']=base['method']+' Specific stopping exceptions are informed by human applicability codes and logged separately.'
    merged['limitations'].append('Accepted stopping exceptions for Marcus/Marco were adjudicated using human | codes; these revised decisions are not independent AI performance.')
    merged['rubric']['applicability_review_policy']={'source':'downloads/stopping_review/policy.json','meaning':data['meaning'],'not_blind':True,'no_extra_graded_points':True}
    data['ws12_merged_review']=merged
    return data

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--human',type=Path,required=True);args=ap.parse_args();data=build(args.human)
    REV.mkdir(exist_ok=True)
    # New revision artifacts only; do not touch human workbook, extraction or scoring files.
    policy={k:v for k,v in data.items() if k!='ws12_merged_review'}
    (REV/'policy.json').write_text(dumps(policy));(REV/'ws12_scoring.json').write_text(dumps(data['ws12_merged_review']))
    site=ROOT/'mmla_explorer/site';(site/'data/structural_stopping.js').write_text('window.STRUCTURAL_STOPPING='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
    download=site/'downloads/stopping_review';download.mkdir(exist_ok=True)
    (download/'policy.json').write_text(dumps(policy));(download/'ws12_scoring.json').write_text(dumps(data['ws12_merged_review']))
    print('Published stopping review data:3 root participant records,13 displayed fields; raw files unchanged.')

if __name__=='__main__':main()
