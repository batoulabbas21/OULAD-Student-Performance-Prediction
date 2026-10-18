"""Independently recompute saved metrics, split safety and PROV fingerprints."""
import argparse,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/learning'))
import numpy as np,pandas as pd
from rdflib import Graph,Namespace,URIRef
from sklearn.metrics import average_precision_score,confusion_matrix
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import VarianceThreshold
from sklearn.preprocessing import StandardScaler
from collections import Counter,defaultdict
from common import sha,read_json,write_json,now

def verify_saved(out):
    out=Path(out);summary=read_json(out/'summary.json');manifest=read_json(out/'manifest.json');checks=[]
    def check(n,b):
        checks.append({'check':n,'passed':bool(b)})
        if not b:raise AssertionError(n)
    check('All recorded input fingerprints match',all(sha(ROOT/n)==h for n,h in manifest['inputs'].items()))
    check('All output fingerprints match',all(sha(out/n)==h for n,h in manifest['outputs'].items()))
    check('Learning checks all passed',summary['passed'] and all(c['passed'] for c in summary['checks']))
    train=pd.read_csv(out/'classification/train-cohort.csv');test=pd.read_csv(out/'classification/test-cohort.csv')
    check('Train/test years and student separation are correct',set(train.presentation)=={'2013J'} and set(test.presentation)=={'2014J'} and not set(train.student)&set(test.student))
    prep=read_json(out/'classification/preprocessing.json');check('Preprocessing fitted exactly the training enrollments',prep['fit_enrollments']==train.enrollment.tolist())
    imp=SimpleImputer(strategy='median',add_indicator=True);imputed=imp.fit_transform(train[prep['feature_names']]);sel=VarianceThreshold();selected=sel.fit_transform(imputed);scale=StandardScaler().fit(selected)
    check('Saved imputation, constant filtering and scaling match training only',np.allclose(imp.statistics_,prep['imputer_statistics']) and imp.get_feature_names_out(prep['feature_names'])[sel.get_support()].tolist()==prep['retained_features'] and np.allclose(scale.mean_,prep['scaler_mean']) and np.allclose(scale.scale_,prep['scaler_scale']))
    pred=pd.read_csv(out/'classification/predictions.csv')
    for m in summary['classification']['metrics']:
        part=pred[(pred.model==m['model'])&(pred.split==m['split'])&(pred.seed==m['seed'])]
        c=confusion_matrix(part.actual,part.predicted,labels=[0,1]).ravel().tolist()
        check(m['split']+'/'+m['model']+': recomputed metrics',len(part)==m['n'] and c==[m[n] for n in ['tn','fp','fn','tp']] and abs(average_precision_score(part.actual,part.score)-m['average_precision'])<1e-10)
        if m['split']=='temporal':check(m['model']+': test labels match source cohort',dict(zip(part.enrollment,part.actual))==dict(zip(test.enrollment,test.label)))
    for se in summary['link_prediction']['seeds']:
        folder=out/'links'/f'seed-{se["seed"]}';splits={n:{tuple(r) for r in pd.read_csv(folder/(n+'.csv')).itertuples(index=False,name=None)} for n in ['train','test','validation','support']}
        check(f'Link seed {se["seed"]}: split disjointness',not splits['train']&(splits['test']|splits['validation']) and not splits['test']&splits['validation'])
        check(f'Link seed {se["seed"]}: no hidden links in support',not any(r=='submitted' for h,r,t in splits['support']))
        ranks=pd.read_csv(folder/'ranks.csv')
        truth=defaultdict(set)
        for h,r,t in splits['train']|splits['test']|splits['validation']:truth[h].add(t)
        counts=Counter(t for h,r,t in splits['train']);meta=pd.read_csv(out/'graph/assessment-metadata.csv');groups=dict(zip(pd.read_csv(out/'graph/labels.csv').enrollment,pd.read_csv(out/'graph/labels.csv').presentation))
        valid=True
        for r in ranks.itertuples():
            pool=meta[meta.offering.str.endswith('/'+groups[r.head])].iri.tolist();filtered=[a for a in pool if a==r.true_tail or a not in truth[r.head]]
            for mode,candidates in [('unfiltered',pool),('filtered',filtered)]:
                expected=1+sum(counts[a]>counts[r.true_tail] for a in candidates)+.5*(sum(counts[a]==counts[r.true_tail] for a in candidates)-1)
                valid=valid and abs(expected-getattr(r,'popularity_'+mode+'_rank'))<1e-10
            valid=valid and len(filtered)==r.filtered_candidate_count and len(pool)==r.candidate_count
        check(f'Link seed {se["seed"]}: popularity ranks and filtering derive from original split counts',valid)
        for model in ['transe','popularity']:
            for mode in ['filtered','unfiltered']:
                rs=ranks[model+'_'+mode+'_rank'].to_numpy();m=se[model+'_'+mode]
                check(f'Link seed {se["seed"]}: {model} {mode} recomputed',abs(np.mean(1/rs)-m['mrr'])<1e-10 and abs(np.mean(rs<=1)-m['hits_at_1'])<1e-10 and abs(np.mean(rs<=3)-m['hits_at_3'])<1e-10)
    prov=Namespace('http://www.w3.org/ns/prov#');g=Graph().parse(out/'provenance.ttl');activity=URIRef('https://example.org/oulad/run/learning/'+summary['run_id'])
    check('PROV input entities match the manifest',set(g.objects(activity,prov.used))=={URIRef('urn:sha256:'+h) for h in manifest['inputs'].values()})
    check('PROV generated entities match output fingerprints',set(g.subjects(prov.wasGeneratedBy,activity))=={URIRef('urn:sha256:'+h) for n,h in manifest['outputs'].items() if n!='provenance.ttl'})
    write_json(out/'verification.json',{'verified_at_utc':now(),'passed':True,'checks':checks,'manifest_sha256':sha(out/'manifest.json')})
    print(f'Saved evidence verification: {len(checks)}/{len(checks)} passed.',flush=True)
    return checks
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path);args=parser.parse_args()
    folder=args.run_dir or ROOT/read_json(ROOT/'outputs/learning/latest.json')['directory'];verify_saved(folder)
