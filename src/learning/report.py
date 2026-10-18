"""Readable result interpretation and scientific comparison figures."""
from common import write_json
import html,json,numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def render(out,summary):
    metrics=pd.DataFrame(summary['classification']['metrics']);temporal=metrics[metrics.split=='temporal']
    lr=temporal[temporal.model=='Logistic regression'].iloc[0];sage=temporal[temporal.model=='GraphSAGE'];count=temporal[temporal.model=='Early submission count'].iloc[0]
    cohort=summary['cohort'];split=summary['classification']['split'];links=summary['link_prediction']['seeds']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
    labels=['Training prevalence','Submission count','Logistic regression','GraphSAGE']
    ap=[temporal[temporal.model=='Training prevalence'].average_precision.iloc[0],count.average_precision,lr.average_precision,sage.average_precision.mean()]
    ax.bar(labels,ap,color=['#95a5a6','#c99542','#287e89','#285a46'],yerr=[0,0,0,sage.average_precision.std(ddof=0)],capsize=5)
    ax.set(ylim=(0,1),ylabel='Average precision (higher is better)',title='Future offering: outcome ranking at day 60')
    ax.tick_params(axis='x',rotation=12)
    for x,y in enumerate(ap):ax.text(x,y+.025,f'{y:.3f}',ha='center')
    fig.savefig(out/'classification-comparison.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    seed0=sage[sage.seed==0].iloc[0]
    for ax,row,title in zip(axes,[lr,seed0],['Logistic regression','GraphSAGE, predefined seed 0']):
        m=np.array([[row.tn,row.fp],[row.fn,row.tp]],dtype=int);ax.imshow(m,cmap='Blues')
        for i in range(2):
            for j in range(2):ax.text(j,i,str(m[i,j]),ha='center',va='center',color='white' if m[i,j]>m.max()/2 else '#153b42',fontsize=18)
        ax.set(xticks=[0,1],xticklabels=['Successful','Unsuccessful'],yticks=[0,1],yticklabels=['Successful','Unsuccessful'],xlabel='Predicted',ylabel='Observed',title=title)
    fig.savefig(out/'confusion-matrices.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
    for ax,mode in zip(axes,['unfiltered','filtered']):
        vals=[[r[name+'_'+mode]['mrr'] for r in links] for name in ['random','popularity','transe']]
        ax.bar(['Random rank','Popularity count','TransE'],[np.mean(x) for x in vals],yerr=[np.std(x) for x in vals],capsize=4,color=['#95a5a6','#c99542','#285a46'])
        ax.set(ylim=(0,1.05),ylabel='Mean reciprocal rank',title=mode.capitalize()+' assessment ranking')
    fig.savefig(out/'link-comparison.png',dpi=180);plt.close(fig)
    rows=''.join(f'<tr><td>{html.escape(str(r.model))}</td><td>{r.seed}</td><td>{r.average_precision:.3f}</td><td>{r.balanced_accuracy:.3f}</td><td>{r.precision:.3f}</td><td>{r.recall:.3f}</td><td>{r.predicted_unsuccessful}</td></tr>' for r in temporal.itertuples())
    lrows=''.join(f'<tr><td>{r["seed"]}</td><td>{r["test_links"]}</td><td>{r["popularity_unfiltered"]["mrr"]:.3f}</td><td>{r["transe_unfiltered"]["mrr"]:.3f}</td><td>{r["popularity_filtered"]["mrr"]:.3f}</td><td>{r["transe_filtered"]["mrr"]:.3f}</td><td>{r["mean_filtered_candidates"]:.2f}</td></tr>' for r in links)
    winner='higher' if sage.average_precision.mean()>lr.average_precision else 'lower'
    lp_better=np.mean([r['transe_filtered']['mrr']-r['popularity_filtered']['mrr'] for r in links])>0
    interpretation=f'GraphSAGE mean AP is {sage.average_precision.mean():.3f} (range {sage.average_precision.min():.3f}–{sage.average_precision.max():.3f}), {winner} than logistic regression ({lr.average_precision:.3f}). This is a comparison on one future offering, not evidence of general superiority.'
    text=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OULAD Session 6 learning results</title>
<style>body{{font:16px/1.65 Segoe UI,Arial;color:#183d42;background:#f3f7f5;margin:0}}main{{max-width:1060px;margin:30px auto;padding:36px;background:white;border-radius:12px}}h1{{font-size:34px}}h2{{margin-top:40px;border-top:1px solid #d8e5e1;padding-top:22px}}a{{color:#076e65}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #dbe5e2}}.table{{overflow:auto}}img{{width:100%;height:auto}}code{{overflow-wrap:anywhere}}.note{{background:#eef6f2;padding:18px;border-left:4px solid #087064}}@media(max-width:700px){{main{{padding:20px;margin:10px}}}}@media print{{main{{margin:0;padding:0}}h2{{break-after:avoid}}img,tr{{break-inside:avoid}}}}</style></head><body><main>
<h1>Learning from the OULAD graph</h1><p>Session 6 · counts, logistic regression, GraphSAGE and TransE</p>
<p class="note"><b>{len(summary['checks'])} checks passed.</b> The historical facts remain separate from learned estimates. Models use the same M2ENV as the labs.</p>
<p><a href="#counts">Original counts</a> · <a href="#classification">Outcome prediction</a> · <a href="#links">Hidden links</a> · <a href="#limits">Limits</a> · <a href="#evidence">Evidence</a></p>
<h2 id="counts">1. What are the initial counts?</h2>
<p>The historical AAA graph has <b>748 enrollments: 531 successful and 217 unsuccessful</b>. Successful means Pass/Distinction; unsuccessful combines Fail/Withdrawn. These labels describe outcomes, not permanent traits of people.</p>
<p>At day 60, {cohort['eligible_day60']} enrollments remain eligible after excluding {cohort['excluded_day60']} already withdrawn/not-yet-registered records. Training uses {split['train_rows']} eligible 2013J enrollments after removing {split['purged_eligible_training_rows']} with student IDs also present in 2014J. The independent 2014J test has <b>{split['test_rows']} enrollments: {split['test_rows']-split['test_unsuccessful']} successful and {split['test_unsuccessful']} unsuccessful</b>.</p>
<p>Compare predicted counts with that same test population. A prediction total should not be compared directly with all 217 historical unsuccessful enrollments. Even an exactly matching total could identify the wrong people; the confusion matrix exposes this.</p>
<h2 id="classification">2. Counts versus outcome models</h2>
<p><b>Question:</b> among enrollments still registered at day 60, can early observations rank eventual Fail/Withdrawn outcomes? Inputs are previous attempts, registration day, submission count, late-submission count and last submission day through day 60. Grades, final results, future withdrawal dates, later submissions, IDs as numerical features, and inferred outcome classes are excluded.</p>
<p>Training prevalence predicts the training majority class for everyone. The submission-count rule ranks fewer observed submissions as higher risk and predicts unsuccessful only when the count is zero. Logistic regression learns a weighted combination of the row features. Two GraphSAGE layers combine those same enrollment values with neighboring early-submission assessment nodes; node features include assessment type, scheduled deadline and weight. Training and test use separate graphs and no shared students.</p>
<img src="classification-comparison.png" alt="Temporal average precision for four models; GraphSAGE error bar is the standard deviation across three training seeds">
<p>{interpretation}</p>
<div class="table"><table><tr><th>Model</th><th>Seed</th><th>AP</th><th>Balanced accuracy</th><th>Precision</th><th>Recall</th><th>Predicted unsuccessful</th></tr>{rows}</table></div>
<p><b>Actual unsuccessful test count: {split['test_unsuccessful']}.</b> AP summarizes the ranking, and the constant-score reference is the test positive fraction ({split['test_unsuccessful']/split['test_rows']:.3f}). AP is average precision, not trapezoidal PR-AUC. Precision answers how many flagged enrollments are truly positive; recall answers how many actual positives were found. Balanced accuracy gives both classes equal weight. Classifiers use a fixed 0.5 threshold, not one tuned on test results. Class weighting means the output scores are not established calibrated risk probabilities.</p>
<img src="confusion-matrices.png" alt="Observed versus predicted counts for logistic regression and the predefined GraphSAGE seed zero">
<p>Rows are observed outcomes; columns are predictions. Top-right counts are false positives; bottom-left counts are missed unsuccessful outcomes. Seed 0 is shown because it was predefined, not because it performed best. All seed results appear above and in the downloadable tables.</p>
<h2>3. Why leakage and splits matter</h2>
<p>The deliberately invalid control feeds the outcome label itself to logistic regression. Its perfect ranking demonstrates how easy it is to get a misleading result; it is excluded from model selection. Three random enrollment splits are also saved as diagnostics. They mix years and can share students, so they do not answer the future-offering question. Each GNN is trained without held-out nodes in its training graph; evaluation may use unlabeled peers from its own held-out cohort.</p>
<p>Features are imputed, stripped of columns constant in training, and scaled using training rows only. Previous-attempt count is zero throughout the temporal training cohort, so it is removed: its effect cannot be learned there. The future test contains returning students, which is a transfer limitation. Hyperparameters, seeds and epochs are recorded in the protocol before model fitting; no test-dependent selection is performed. The three GraphSAGE seeds vary initialization on the same temporal test. Their spread is not a population confidence interval.</p>
<h2 id="links">4. Does TransE beat the popularity count?</h2>
<p>There are <b>3,107 distinct nonbanked historical enrollment → assessment links</b>, after excluding 42 banked records. For each seed, 80% train, 10% validation and 10% test are selected at the link level (rounded down for validation and test). Validation is reserved; there is no early stopping or tuning. The model also sees offering membership and assessment types, but no assessment-record nodes, scores or outcome facts that could reconstruct a hidden edge directly.</p>
<p>TransE learns vectors so head + relation lies near tail. The baseline ranks assessments by their training submission counts. Both rank the same six scheduled assessments in the enrollment's offering, including the exam with no observed result links. This is a historical reconstruction exercise, <b>not prediction of future submissions or a recommendation</b>.</p>
<img src="link-comparison.png" alt="TransE versus popularity and random rank baselines, using unfiltered and filtered MRR">
<div class="table"><table><tr><th>Seed</th><th>Hidden links</th><th>Count MRR raw</th><th>TransE MRR raw</th><th>Count MRR filtered</th><th>TransE MRR filtered</th><th>Mean filtered candidates</th></tr>{lrows}</table></div>
<p>TransE's mean filtered MRR is {'above' if lp_better else 'below'} the popularity baseline in this run. MRR averages 1/rank: rank 1 gives 1, rank 2 gives 0.5. Hits@1 and Hits@3 are in the summary and per-seed reports. Ties use the average (realistic) rank; raw entity IDs never break a score tie.</p>
<p>Unfiltered evaluation ranks all six candidates. Filtered evaluation removes other known true links using the original truth only during scoring. Many students already submitted most assignments, leaving few candidates; therefore filtered scores can look high even for simple baselines. The plots include a random-ranking expectation for those exact candidate-set sizes. Exam non-observation is not proof that exams were not taken. Sampled unobserved links in training are contrasts, not verified negative facts.</p>
<h2 id="limits">5. What these results establish</h2>
<p>The outcome experiment tests transfer from one earlier offering to one later offering with repeat-student separation. The link experiment tests reconstruction of masked historical edges. Neither establishes causal effects, performance on another module, or suitability for operational student decisions. AAA has few shared assessment nodes; a GNN may add little beyond submission counts. No click activity was loaded. Submission and registration dates are used as availability proxies because the release has no ingestion/revision log. Scores are excluded because grade-publication timestamps are absent.</p>
<p>Predictions remain separate files and do not overwrite source outcomes, OWL memberships or validated historical facts. The existing ontology reasons from known facts; the learning models estimate unknown labels or missing links and can be wrong.</p>
<h2 id="evidence">6. Open the evidence</h2>
<ul><li><a href="classification/metrics.csv">All classification metrics, including random splits and invalid control</a></li><li><a href="classification/predictions.csv">Per-enrollment predictions</a></li><li><a href="classification/logistic-coefficients.csv">Logistic coefficients</a></li><li><a href="graph/learning-input.ttl">Label-free learning RDF</a> and <a href="graph/cohort.json">cohort counts</a></li><li><a href="links/all-ranks.csv">Per-link ranks</a> and <a href="links/summary.json">all link metrics</a></li><li><a href="summary.json">Complete run summary</a>, <a href="checks.json">checks</a>, <a href="provenance.ttl">provenance</a>, <a href="manifest.json">input/output fingerprints</a></li></ul>
<p>Run <code>{summary['run_id']}</code><br>Started {summary['started_at_utc']}<br>Checks completed {summary['finished_at_utc']} (UTC). Figures use actual measured results.</p>
</main></body></html>"""
    (out/'report.html').write_text(text,encoding='utf-8')
    return {'classification_conclusion':interpretation,'link_transe_mean_filtered_mrr_above_count':bool(lp_better)}
