"""Fixed-protocol counts, logistic regression and inductive GraphSAGE comparisons."""
import numpy as np,pandas as pd,torch
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score,roc_auc_score,accuracy_score,balanced_accuracy_score,precision_score,recall_score,f1_score,confusion_matrix
from torch_geometric.nn import SAGEConv
from common import write_json
from build_graph import FEATURES
torch.set_num_threads(1)
def metrics(y,score,pred):
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'n':len(y),'actual_unsuccessful':int(np.sum(y)),'predicted_unsuccessful':int(np.sum(pred)),
        'average_precision':float(average_precision_score(y,score)),'roc_auc':float(roc_auc_score(y,score)),
        'accuracy':float(accuracy_score(y,pred)),'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
        'precision':float(precision_score(y,pred,zero_division=0)),'recall':float(recall_score(y,pred,zero_division=0)),
        'f1':float(f1_score(y,pred,zero_division=0)),'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}
def make_graph(frame,assessments,early,x):
    # Separate graphs for training and evaluation: held-out nodes never send training messages.
    edges=early[early.enrollment.isin(frame.enrollment)]
    ai=assessments[assessments.iri.isin(edges.assessment)].sort_values('iri').reset_index(drop=True)
    eidx={k:i for i,k in enumerate(frame.enrollment)};aidx={k:i for i,k in enumerate(ai.iri)}
    width=x.shape[1];features=np.zeros((len(frame)+len(ai),width+6),dtype=np.float32)
    features[:len(frame),:width]=x;features[:len(frame),width]=1
    for j,r in ai.iterrows():
        features[len(frame)+j,width+1:]=[0 if pd.isna(r.deadline) else float(r.deadline)/365,float(r.weight)/100,
                int(r.type=='TutorMarkedAssessment'),int(r.type=='ComputerMarkedAssessment'),int(r.type=='Exam')]
    pairs=[]
    for r in edges.itertuples():
        u=eidx[r.enrollment];v=len(frame)+aidx[r.assessment];pairs.extend([(u,v),(v,u)])
    index=torch.tensor(pairs,dtype=torch.long).T.contiguous() if pairs else torch.empty((2,0),dtype=torch.long)
    return torch.tensor(features),index
class SAGE(torch.nn.Module):
    def __init__(self,width,hidden):
        super().__init__();self.first=SAGEConv(width,hidden);self.second=SAGEConv(hidden,hidden);self.score=torch.nn.Linear(hidden,1)
    def forward(self,x,edge_index):return self.score(self.second(self.first(x,edge_index).relu(),edge_index).relu()).flatten()
def execute(rows,assessments,early,out,protocol):
    out.mkdir(parents=True,exist_ok=True);eligible=rows[rows.eligible].copy()
    future_students=set(rows.loc[rows.presentation==protocol['test_presentation'],'student'])
    past=eligible[eligible.presentation==protocol['train_presentation']]
    train=past[~past.student.isin(future_students)].reset_index(drop=True)
    test=eligible[eligible.presentation==protocol['test_presentation']].reset_index(drop=True)
    assert not set(train.student)&set(test.student)
    train.to_csv(out/'train-cohort.csv',index=False);test.to_csv(out/'test-cohort.csv',index=False)
    excluded=past[past.student.isin(future_students)];excluded.to_csv(out/'purged-training-overlap.csv',index=False)
    split={'train_rows':len(train),'test_rows':len(test),'purged_eligible_training_rows':len(excluded),
        'all_cross_offering_students':len(set(rows[rows.presentation==protocol['train_presentation']].student)&future_students),
        'train_unsuccessful':int(train.label.sum()),'test_unsuccessful':int(test.label.sum()),'student_overlap':0}
    write_json(out/'split.json',split)
    all_metrics=[];predictions=[];coefficients=[]
    def save(name,split_name,seed,frame,score,pred):
        result={'model':name,'split':split_name,'seed':seed,**metrics(frame.label.to_numpy(),score,pred)};all_metrics.append(result)
        for row,s,p in zip(frame.itertuples(),score,pred):predictions.append({'model':name,'split':split_name,'seed':seed,'enrollment':row.enrollment,'actual':row.label,'score':float(s),'predicted':int(p)})
        print(f'{split_name} {name} seed {seed}: AP {result["average_precision"]:.3f}, predicted {result["predicted_unsuccessful"]}/{result["n"]}; actual {result["actual_unsuccessful"]}',flush=True)
    def fit_pair(tr,te,label,seeds):
        prep=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),VarianceThreshold(),StandardScaler())
        xt=prep.fit_transform(tr[FEATURES]);xe=prep.transform(te[FEATURES])
        lr=LogisticRegression(**protocol['logistic'],random_state=0).fit(xt,tr.label)
        p=lr.predict_proba(xe)[:,1];save('Logistic regression',label,0,te,p,p>=protocol['threshold'])
        if label=='temporal':
            all_names=prep[0].get_feature_names_out(FEATURES);names=all_names[prep[1].get_support()]
            coefficients.extend({'feature':n,'standardized_coefficient':float(c)} for n,c in zip(names,lr.coef_[0]))
            write_json(out/'preprocessing.json',{'feature_names':FEATURES,'imputer_statistics':prep[0].statistics_.tolist(),'retained_features':names.tolist(),'dropped_constant_features':all_names[~prep[1].get_support()].tolist(),'scaler_mean':prep[2].mean_.tolist(),'scaler_scale':prep[2].scale_.tolist(),'fit_enrollments':tr.enrollment.tolist()})
            write_json(out/'logistic-model.json',{'coefficient':lr.coef_[0].tolist(),'intercept':lr.intercept_.tolist(),'classes':lr.classes_.tolist()})
        for name,score,pred in [('Training prevalence',np.full(len(te),tr.label.mean()),np.full(len(te),tr.label.mean()>=.5)),
                    ('Early submission count',-te.early_submission_count.to_numpy(),te.early_submission_count.to_numpy()==0)]:save(name,label,0,te,score,pred)
        tg=make_graph(tr,assessments,early,xt);eg=make_graph(te,assessments,early,xe)
        for seed in seeds:
            torch.manual_seed(seed);torch.use_deterministic_algorithms(True)
            model=SAGE(tg[0].shape[1],protocol['graphsage']['hidden']);opt=torch.optim.Adam(model.parameters(),lr=protocol['graphsage']['learning_rate'])
            y=torch.tensor(tr.label.to_numpy(),dtype=torch.float32);weight=torch.tensor(float((1-tr.label.mean())/tr.label.mean()))
            for _ in range(protocol['graphsage']['epochs']):
                model.train();opt.zero_grad();logits=model(*tg)[:len(tr)]
                loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y,pos_weight=weight);loss.backward();opt.step()
            model.eval()
            with torch.no_grad():p=torch.sigmoid(model(*eg)[:len(te)]).numpy()
            save('GraphSAGE',label,seed,te,p,p>=protocol['threshold'])
            if label=='temporal':torch.save(model.state_dict(),out/f'graphsage-seed-{seed}.pt')
        return prep
    fit_pair(train,test,'temporal',protocol['classification_seeds'])
    # Deliberately leaky control, clearly separate from valid models. It exposes the answer itself.
    bad=LogisticRegression(C=1,max_iter=2000).fit(train[['label']],train.label)
    bp=bad.predict_proba(test[['label']])[:,1];save('INVALID label-leak control','leak_control',0,test,bp,bp>=.5)
    diagnostics=[]
    for seed in protocol['random_split_seeds']:
        tr,te=train_test_split(eligible,test_size=protocol['random_test_share'],stratify=eligible.label,random_state=seed)
        diagnostics.append({'seed':seed,'train_rows':len(tr),'test_rows':len(te),'overlapping_students':len(set(tr.student)&set(te.student))})
        fit_pair(tr.reset_index(drop=True),te.reset_index(drop=True),f'random_{seed}',[seed])
    pd.DataFrame(all_metrics).to_csv(out/'metrics.csv',index=False);pd.DataFrame(predictions).to_csv(out/'predictions.csv',index=False)
    pd.DataFrame(coefficients).to_csv(out/'logistic-coefficients.csv',index=False);write_json(out/'random-split-diagnostics.json',diagnostics)
    return {'split':split,'metrics':all_metrics,'random_split_diagnostics':diagnostics,'graphsage_seeds':protocol['classification_seeds']}
