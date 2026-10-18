"""Historical missing-link reconstruction: TransE versus training popularity counts."""
from common import write_json
import collections,numpy as np,pandas as pd,torch
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory

def rank(scores,index):
    s=np.asarray(scores);target=s[index]
    return float(1+np.sum(s>target)+0.5*(np.sum(s==target)-1))
def aggregate(ranks):
    r=np.asarray(ranks,dtype=float)
    return {'mrr':float(np.mean(1/r)),'hits_at_1':float(np.mean(r<=1)),'hits_at_3':float(np.mean(r<=3)),'n':len(r)}
def execute(rows,assessments,records,out,protocol):
    out.mkdir(parents=True,exist_ok=True)
    attempts=sorted({(r.enrollment,'submitted',r.assessment) for r in records[records.banked==False].itertuples()})
    support=set()
    for r in rows.itertuples():support.add((r.enrollment,'inOffering',r.offering))
    for r in assessments.itertuples():
        support.add((r.iri,'assessmentInOffering',r.offering));support.add((r.iri,'assessmentType','https://example.org/oulad/assessment-type/'+r.type))
    known=collections.defaultdict(set)
    for h,_,t in attempts:known[h].add(t)
    offering=dict(zip(rows.enrollment,rows.offering))
    candidates={o:sorted(assessments.loc[assessments.offering==o,'iri']) for o in assessments.offering.unique()}
    cfg=protocol['link_prediction'];summaries=[];all_ranks=[]
    for seed in cfg['seeds']:
        dest=out/f'seed-{seed}';dest.mkdir()
        perm=np.random.default_rng(seed).permutation(len(attempts));n=int(len(attempts)*cfg['test_share']);nv=int(len(attempts)*cfg['validation_share'])
        test=[attempts[i] for i in perm[:n]];valid=[attempts[i] for i in perm[n:n+nv]];train=[attempts[i] for i in perm[n+nv:]]
        assert not set(train)&(set(test)|set(valid)) and not set(test)&set(valid)
        tf=TriplesFactory.from_labeled_triples(np.array(train+sorted(support)))
        make=lambda data:TriplesFactory.from_labeled_triples(np.array(data),entity_to_id=tf.entity_to_id,relation_to_id=tf.relation_to_id)
        for name,triples in [('train',train),('validation',valid),('test',test),('support',sorted(support))]:pd.DataFrame(triples,columns=['head','relation','tail']).to_csv(dest/(name+'.csv'),index=False)
        print(f'TransE seed {seed}: {len(train)} training links, {len(test)} hidden test links',flush=True)
        result=pipeline(training=tf,validation=make(valid),testing=make(test),model='TransE',
            model_kwargs={'embedding_dim':cfg['dimension'],'scoring_fct_norm':1},optimizer='Adam',optimizer_kwargs={'lr':cfg['learning_rate']},
            training_kwargs={'num_epochs':cfg['epochs'],'batch_size':cfg['batch_size'],'use_tqdm':False,'pin_memory':False},
            negative_sampler='basic',negative_sampler_kwargs={'num_negs_per_pos':cfg['negatives_per_positive'],'filtered':True},
            random_seed=seed,device='cpu',use_tqdm=False,evaluation_kwargs={'use_tqdm':False,'batch_size':64})
        model=result.model;model.eval();torch.save(model.state_dict(),dest/'transe.pt')
        write_json(dest/'training.json',{'losses':result.losses,'entities':tf.entity_to_id,'relations':tf.relation_to_id,
            'negative_sampling':'Basic corruption over entities; filters training positives only. Unknown links are sampled contrasts, not verified false statements.',
            'validation':'Reserved for evaluation filtering; fixed epochs, no early stopping or model selection.'})
        pop=collections.Counter(t for _,_,t in train);seen_heads={h for h,_,_ in train};entries=[];sizes=[];chance=[]
        for h,r,t in test:
            cand=candidates[offering[h]];keep=[i for i,a in enumerate(cand) if a==t or a not in known[h]]
            batch=torch.tensor([[tf.entity_to_id[h],tf.relation_to_id[r],tf.entity_to_id[a]] for a in cand])
            with torch.no_grad():scores=model.score_hrt(batch).flatten().cpu().numpy()
            idx=cand.index(t);baseline=np.asarray([pop[a] for a in cand],dtype=float)
            row={'seed':seed,'head':h,'true_tail':t,'candidate_count':len(cand),'filtered_candidate_count':len(keep),
                 'transe_unfiltered_rank':rank(scores,idx),'popularity_unfiltered_rank':rank(baseline,idx),
                 'transe_filtered_rank':rank(scores[keep],keep.index(idx)),'popularity_filtered_rank':rank(baseline[keep],keep.index(idx)),
                 'no_training_submission_for_head':h not in seen_heads}
            entries.append(row);sizes.append(len(keep));chance.append(sum(1/j for j in range(1,len(keep)+1))/len(keep))
        pd.DataFrame(entries).to_csv(dest/'ranks.csv',index=False)
        row={'seed':seed,'initial_links':len(attempts),'train_links':len(train),'validation_links':len(valid),'test_links':len(test),'support_links':len(support),
            'cold_entity_test_links':0,'test_links_with_zero_training_degree':sum(x['no_training_submission_for_head'] for x in entries),
            'mean_filtered_candidates':float(np.mean(sizes)),'min_filtered_candidates':min(sizes),'max_filtered_candidates':max(sizes),
            'random_unfiltered':{'mrr':sum(1/j for j in range(1,7))/6,'hits_at_1':1/6,'hits_at_3':.5},
            'random_filtered':{'mrr':float(np.mean(chance)),'hits_at_1':float(np.mean(1/np.asarray(sizes))),'hits_at_3':float(np.mean(np.minimum(3,np.asarray(sizes))/np.asarray(sizes)))}}
        for name in ['transe','popularity']:
            for mode in ['filtered','unfiltered']:row[name+'_'+mode]=aggregate([x[name+'_'+mode+'_rank'] for x in entries])
        write_json(dest/'summary.json',row);summaries.append(row);all_ranks.extend(entries)
        print(f'Seed {seed}: filtered MRR TransE {row["transe_filtered"]["mrr"]:.3f}, count {row["popularity_filtered"]["mrr"]:.3f}; unfiltered {row["transe_unfiltered"]["mrr"]:.3f} / {row["popularity_unfiltered"]["mrr"]:.3f}',flush=True)
    pd.DataFrame(all_ranks).to_csv(out/'all-ranks.csv',index=False);write_json(out/'summary.json',summaries)
    return {'seeds':summaries,'initial_links':len(attempts),'candidate_policy':'Six scheduled assessments in the same offering, including the exam with no observed submission links.',
        'task':'Retrospective hidden-link reconstruction, not future participation prediction or recommendation.'}
