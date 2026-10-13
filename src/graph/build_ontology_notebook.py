"""Create and execute a readable ontology results notebook using the current Python environment."""
from pathlib import Path
import sys

import nbformat as nbf
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[2]


def main():
    cells = []
    md = lambda text: cells.append(nbf.v4.new_markdown_cell(text))
    code = lambda text: cells.append(nbf.v4.new_code_cell(text))
    md('''# OULAD: what the ontology adds

This notebook explains the Session 3 OWL extension of the AAA project. It reads the actual
HermiT results and CSV reconciliation checks. It does not rerun the reasoner or change the databases.
Use the existing **M2ENV** Python kernel when rerunning cells.

**Facts** say which student enrolled and which score was recorded. **Definitions** explain
what classes such as `SuccessfulEnrollment` mean. **Inference** identifies individuals
that satisfy those definitions without explicitly asserting their new type.

Run the README's Session 3 commands before this notebook if outputs are missing or stale.''')
    code('''from pathlib import Path
import hashlib, json, sys
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from IPython.display import display
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'src/graph/prepare_ontology.py').exists())
OUT = ROOT / 'outputs/ontology'
EDU = Namespace('https://example.org/oulad/schema#')
full = json.loads((OUT / 'reasoned-full.json').read_text(encoding='utf-8'))
verification = json.loads((OUT / 'verification.json').read_text(encoding='utf-8'))
preparation = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
for report in [full, verification]:
    for name, digest in report['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'Stale results: rerun README Session 3 commands.'
assert full['consistent'] and not full['unsatisfiable_classes']
assert verification['passed']
facts = Graph().parse(ROOT / 'data/processed/oulad.ttl')
inferred = Graph().parse(OUT / 'inferred-types-full.ttl')
sys.path.insert(0, str(ROOT / 'src/graph'))
from owl_reasoner import merged_graph
ontology = merged_graph(OUT / 'workspace/education.owl.ttl')
print('Python:', sys.executable)
print('Verified:', full['verified_at_utc'])
print('Asserted data triples:', len(facts), '| New named type assertions:', len(inferred))
print('Consistent: yes | Unsatisfiable named classes: none')
print('Checks passed:', len(verification['checks']))''')
    md('''## 1. The existing relationships

Each arrow below is an object property, read from the ontology's domain and range.
For example, an **Enrollment hasStudent Student**. A Student is a person; an Enrollment
is that person's participation in one offering. Outcome belongs to the enrollment.''')
    code('''positions = {'Student': (0, 2), 'Enrollment': (2, 2), 'CourseOffering': (4, 2),
             'Module': (6, 2), 'AssessmentRecord': (2, 0), 'Assessment': (4, 0), 'LearningResource': (6, 0)}
properties = ['hasStudent', 'inOffering', 'offeringOf', 'recordForEnrollment',
              'forAssessment', 'assessmentInOffering', 'resourceInOffering']
relations = []
network = nx.DiGraph()
for name in properties:
    source = str(ontology.value(EDU[name], RDFS.domain)).split('#')[-1]
    target = str(ontology.value(EDU[name], RDFS.range)).split('#')[-1]
    relations.append({'from class': source, 'property': name, 'to class': target})
    network.add_edge(source, target, label=name)
fig, ax = plt.subplots(figsize=(16, 6))
nx.draw_networkx_nodes(network, positions, node_color='#dbeafe', node_size=5600, node_shape='s', ax=ax)
labels = {name: name.replace('AssessmentRecord', 'Assessment\\nRecord').replace('CourseOffering', 'Course\\nOffering').replace('LearningResource', 'Learning\\nResource') for name in network.nodes}
nx.draw_networkx_labels(network, positions, labels=labels, font_size=10, ax=ax)
nx.draw_networkx_edges(network, positions, arrowsize=20, node_size=5600, node_shape='s', ax=ax)
for (source, target), label in nx.get_edge_attributes(network, 'label').items():
    x1, y1 = positions[source]; x2, y2 = positions[target]
    vertical = x1 == x2
    ax.text((x1+x2)/2 - (0.12 if vertical else 0), (y1+y2)/2, label,
            fontsize=8, ha='right' if vertical else 'center', va='center',
            bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 2})
ax.set_xlim(-0.9, 6.9); ax.set_ylim(-0.7, 2.7); ax.axis('off')
plt.show()
display(pd.DataFrame(relations))''')
    md('''## 2. Questions become definitions

These six classes answer specific project questions. `EquivalentTo` lets the reasoner
classify an individual from the facts. A one-way `SubClassOf` restriction alone does not
provide that reverse direction.

| Class | Meaning |
|---|---|
| SuccessfulEnrollment | Enrollment with outcome Pass or Distinction |
| WithdrawnEnrollment | Enrollment with outcome Withdrawn |
| LowScoreAssessmentRecord | AssessmentRecord with a known score strictly below 40 |
| BankedAssessmentRecord | AssessmentRecord with isBanked true |
| NonBankedAssessmentRecord | AssessmentRecord with isBanked false |
| EnrollmentWithLowScore | Enrollment with at least one low-score assessment record |

`hasAssessmentRecord` is the inverse of `recordForEnrollment`. It connects an enrollment
to its recorded results for the final definition. No rule says a low score implies final Fail.''')
    code('''display(pd.DataFrame(verification['inferred_counts']))

hierarchy = []
short = lambda iri: iri.split('#')[-1].rsplit('/', 1)[-1]
for cls, parents in full['class_parents'].items():
    hierarchy.append({'class': short(cls), 'inferred direct named parents': ', '.join(short(p) for p in parents)})
display(pd.DataFrame(hierarchy).sort_values('class'))''')
    md('''## 3. See the evidence for an inferred type

The following rows select one real individual for each new class. The extra type is
inferred; the score, flag, outcome or linked record is present in the original RDF.''')
    code('''examples = []
for row in verification['inferred_counts']:
    name = row['class']
    matches = sorted(iri for iri, kinds in full['types'].items() if str(EDU[name]) in kinds)
    if not matches:
        continue
    iri = URIRef(matches[0])
    if name in ['SuccessfulEnrollment', 'WithdrawnEnrollment']:
        evidence = 'finalResult = ' + str(facts.value(iri, EDU.finalResult))
    elif name == 'LowScoreAssessmentRecord':
        evidence = 'score = ' + str(facts.value(iri, EDU.score))
    elif name in ['BankedAssessmentRecord', 'NonBankedAssessmentRecord']:
        evidence = 'isBanked = ' + str(facts.value(iri, EDU.isBanked))
    else:
        low_records = sorted(r for r in facts.subjects(EDU.recordForEnrollment, iri)
                             if facts.value(r, EDU.score) is not None and float(facts.value(r, EDU.score)) < 40)
        chosen = low_records[0]
        evidence = str(chosen).split('/id/')[-1] + ' has score ' + str(facts.value(chosen, EDU.score))
    examples.append({'inferred class': name, 'individual': str(iri).split('/id/')[-1],
                     'evidence': evidence, 'type explicitly asserted?': (iri, RDF.type, EDU[name]) in facts})
display(pd.DataFrame(examples))''')
    md('''## 4. Query facts before and after adding inferred types

The same SPARQL query returns no successful-enrollment types in the original facts.
After we add the exported inferred type assertions locally, it returns the inferred count.
This does not change Fuseki: the graphs in this cell exist only in the notebook.''')
    code('''query = """PREFIX edu: <https://example.org/oulad/schema#>
SELECT (COUNT(DISTINCT ?enrollment) AS ?n)
WHERE { ?enrollment a edu:SuccessfulEnrollment }
"""
combined = facts + inferred
display(pd.DataFrame([
    {'graph': 'Original asserted facts', 'successful enrollments': int(next(iter(facts.query(query)))[0])},
    {'graph': 'Facts + inferred named types', 'successful enrollments': int(next(iter(combined.query(query)))[0])}
]))

comparison = """PREFIX edu: <https://example.org/oulad/schema#>
SELECT ?outcome (COUNT(DISTINCT ?enrollment) AS ?count)
WHERE { ?enrollment a edu:EnrollmentWithLowScore ; edu:finalResult ?outcome }
GROUP BY ?outcome ORDER BY ?outcome
"""
result = combined.query(comparison)
display(pd.DataFrame([[str(v) for v in row] for row in result], columns=['outcome', 'enrollments with a low score']))''')
    md('''## 5. What the small teaching sample contains

The sample deliberately covers each outcome plus a low score, a banked result and an unknown
score. It retains real identifiers and facts; labels and individual declarations are added
for readability. Its counts are not estimates for all students.''')
    code('''display(pd.DataFrame([
    {'enrollment': iri.split('/id/')[-1], 'selected because': '; '.join(reasons)}
    for iri, reasons in preparation['selected_enrollments'].items()
]))
print('Sample individuals:', preparation['sample_individuals'])
print('Retained source triples:', preparation['sample_source_triples'])''')
    md('''## 6. Session 3 traps, tested with synthetic examples

- **Open world:** an absent score is unknown. It is not zero and does not imply a low score.
- **Exactly one:** OWL can satisfy an unstated link without an explicit RDF value. Use SHACL for required fields.
- **Names are not identities:** two student IRIs may denote the same person unless explicitly distinguished.
- **Some and only:** `only` restricts possible values; `some` also says that a value exists.
- **Domain errors:** using `hasStudent` on a Student forces the subject to be an Enrollment too.
  Those types are disjoint in this model. An impossible empty class can coexist with a consistent
  ontology; asserting an instance of it makes the ontology inconsistent.

The bad examples are separate teaching files, never added to the real RDF or database.''')
    code('''display(pd.DataFrame([
    {'check': item['check'], 'passed': item['passed'],
     'detail': item['detail'] if isinstance(item['detail'], str) else json.dumps(item['detail'])}
    for item in verification['checks']
]))''')
    md('''## 7. Reuse and limits

The project imports a **selected FOAF Person/Agent fragment**, extracted from a cached official
snapshot. It retains the published IRIs and the Person-subclass-of-Agent axiom. It is not a
complete FOAF import. See `ontology/imports/README.md` for provenance, license, and selection.

Lateness still requires the existing SPARQL comparison of submission day with deadline.
The exported Turtle contains **new named type assertions**, not the complete OWL closure.
Fuseki and Neo4j do not automatically receive these results. The successful-enrollment classes
describe historical outcomes and must not become input features for a future-outcome predictor.

The README documents the full commands and the distinction between authored ontology files,
generated workspace files, real observations and synthetic test cases.''')
    notebook = nbf.v4.new_notebook(cells=cells, metadata={
        'kernelspec': {'display_name': 'Python (select M2ENV)', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': sys.version.split()[0]}})
    directory = ROOT / 'notebooks'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / '03_ontology_results.ipynb'
    nbf.write(notebook, target)
    # Use exactly the interpreter running this script; no kernel installation or env changes.
    manager = KernelManager(kernel_name='python3')
    manager.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
    try:
        client = NotebookClient(notebook, km=manager, timeout=180,
                                resources={'metadata': {'path': str(ROOT)}})
        client.execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbf.write(notebook, target)
    html, _ = HTMLExporter(template_name='lab').from_notebook_node(notebook)
    preview = ROOT / 'outputs/ontology/ontology-results.html'
    preview.write_text(html, encoding='utf-8')
    print('Executed notebook:', target)
    print('HTML preview:', preview)


if __name__ == '__main__':
    main()
