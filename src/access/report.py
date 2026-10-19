"""Readable HTML evidence; all model text is escaped before display."""
import html,json
from common import OUT
CSS='''body{font:17px/1.6 system-ui,sans-serif;color:#182c3b;background:#eef4f7;margin:0}main{max-width:1120px;margin:35px auto;padding:38px;background:white;border-radius:16px}h1,h2{line-height:1.2;color:#163f57}h1{font-size:40px}table{border-collapse:collapse;width:100%;margin:20px 0}td,th{padding:11px;text-align:left;border-bottom:1px solid #ccdce5}th{background:#e7f1f6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf3f6;padding:16px;font:14px/1.5 monospace}details{margin:12px 0;padding:12px;border:1px solid #ccdce5;border-radius:8px}.note{background:#fff2d4;padding:18px;border-radius:8px}a{color:#006a86}.scroll{overflow:auto}@media print{body{background:white}main{margin:0;padding:0}details{break-inside:avoid}}'''
def esc(x):return html.escape(str(x))
def page(title,body):return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>'+CSS+'</style><main><h1>'+esc(title)+'</h1>'+body+'</main></html>'
def write_report(folder,summary,records):
    body=f'<p>Run <code>{esc(summary["run_id"])}</code> · {esc(summary["mode"])} · {esc(summary["model"])}</p>'
    body+='<p class="note">These scores evaluate generated queries against actual answer rows. Passing the parser and vocabulary checks does not establish that a query answers the question correctly. This is a small, authored benchmark, not a general accuracy guarantee.</p>'
    body+='<div class="scroll"><table><tr><th>Setting</th><th>Mean row F1</th><th>Exact answers</th><th>Correct refusals</th><th>Successful repairs</th></tr>'
    for s,v in summary['settings'].items():body+=f'<tr><td>{s}</td><td>{v["mean_row_f1"]:.3f}</td><td>{v["exact_answers"]}/{v["answerable"]}</td><td>{v["correct_refusals"]}/{v["unanswerable"]}</td><td>{v["successful_repairs"]}</td></tr>'
    body+='</table></div><p>Schema = rules + observed schema. Examples = add the three closest worked questions. Repair = add vocabulary checks and up to two correction attempts. All settings enforce local read-only queries and execution limits.</p>'
    body+='<h2>Questions, answers and checks</h2><p>Expand any question to see the returned rows, expected answer and each attempted query. Refusal is scored separately from answer F1.</p>'
    for row in records:
        r=row['response'];label='correct refusal' if row.get('correct_refusal') else ('F1 '+format(row['score']['f1'],'.3f') if row.get('score') else r['status'])
        body+='<details><summary>'+esc(row['setting']+' · '+row['id']+' · '+label+' · '+row['question'])+'</summary><pre>'+esc(json.dumps(row,indent=2,ensure_ascii=False))+'</pre></details>'
    body+='<h2>Read next</h2><p><a href="../../../../docs/access-results-explained.html">Detailed explanation and interpretation</a> · <a href="summary.json">Summary</a> · <a href="manifest.json">File fingerprints</a> · <a href="provenance.ttl">Run provenance</a></p>'
    (folder/'report.html').write_text(page('OULAD · Session 7 results',body),encoding='utf-8')
    relative=folder.relative_to(OUT).as_posix()+'/report.html'
    (OUT/'access-results.html').write_text(page('Open the Session 7 results','<p><a href="'+relative+'">Open the latest evaluated run</a></p>'),encoding='utf-8')
