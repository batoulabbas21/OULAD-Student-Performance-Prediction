"""Independent answers from selected CSV rows, never from a model or its SPARQL."""
import pandas as pd
from common import ROOT

def expected():
    folder=ROOT/'data/interim';si=pd.read_csv(folder/'studentInfo.csv');sa=pd.read_csv(folder/'studentAssessment.csv');ass=pd.read_csv(folder/'assessments.csv')
    joined=sa.merge(ass,on='id_assessment',validate='many_to_one')
    values={'students':si.id_student.nunique(),'enrollments_2014':int((si.code_presentation=='2014J').sum()),
        'assessments':len(ass),'late':int(((joined.is_banked==0)&(joined.date_submitted>joined.date)).sum()),
        'low':int((sa.score<40).sum()),'unknown':int(sa.score.isna().sum()),'banked':int((sa.is_banked==1).sum()),
        'success':int(si.final_result.isin(['Pass','Distinction']).sum()),'unknown_deadline':int(ass.date.isna().sum())}
    out={k:{'columns':['count'],'rows':[{'count':str(v)}]} for k,v in values.items()}
    counts=si.groupby(['code_presentation','final_result']).size()
    out['outcomes']={'columns':['presentation','result','count'], 'rows':[{'presentation':p,'result':r,'count':str(n)} for (p,r),n in counts.items()]}
    return out
