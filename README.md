# OULAD knowledge representation project — first working stages

This starter implements download, relational subsetting, profiling, RDF conversion,
RDFS schema, SPARQL questions, and a small RDFS entailment demonstration.
It reuses the lab techniques and the existing Conda environment; it does not modify the course labs.
No Docker service, API key, LLM, package upgrade, or new environment is needed for the RDF/RDFS core.
The optional Neo4j visualization below uses the existing lab Neo4j Docker service.

**What is AAA?** An anonymized Social Sciences module with two October offerings (2013J and 2014J).
Our extract has 748 enrollments but 712 distinct student IDs. Read [the AAA explanation](docs/aaa-module.md)
for the offering lengths, assessment schedule, outcomes, and limitations of the anonymized data.

## Run it, step by step

Open an Anaconda Prompt or a PowerShell terminal configured for Conda. Run from the project root.

```powershell
conda activate M2ENV
Set-Location 'C:\Users\user\OneDrive\Desktop\M2\kr-oulad'

# 1. Download once; existing original files are verified on later runs.
python src/preparation/fetch_data.py

# 2. Inspect the original core tables.
python src/preparation/profiling.py --raw

# 3. Keep one complete module across its offerings.
python src/preparation/select_subset.py --module AAA

# 4. Profile the selected data and inspect the rule checks.
python src/preparation/profiling.py

# 5. Convert the selected tables to RDF using the supplied RDFS vocabulary.
python src/graph/convert_to_rdf.py

# 6. Run the competency questions.
python src/graph/run_queries.py

# 7. Demonstrate RDFS inference on a small real-data sample.
python src/graph/rdfs_entailment_demo.py

# 8. Compare CSV/SQL answers with RDF/SPARQL answers.
python evaluation/verify.py
```

Run each command only after the previous one succeeds. If your lab environment has another name,
replace M2ENV; the project folder does not contain or need its own environment.
The data and core outputs have already been generated in this working copy; rerunning is supported.

| After the step | Open or inspect |
|---|---|
| Download | data/raw/manifest.json and the seven CSVs |
| Raw profiling | outputs/profiling/raw/profile.html |
| Selection | data/interim/selection.json |
| Subset profiling | outputs/profiling/subset/profile.html and rule_checks.csv |
| RDF | data/processed/oulad.ttl and graph_summary.json |
| RDFS vocabulary | ontology/education.rdfs.ttl (authored schema, separate from generated facts) |
| Questions | outputs/answers/*.csv and status.json |
| RDFS reasoning | outputs/rdfs/explanation.md and sample_inferred.ttl |
| Verification | outputs/verification.json; expect 14 passed checks for the core subset |

Recorded core run on 2026-10-10: 2 offerings, 748 enrollments, 12 assessments,
3,149 assessment records, 413 resource descriptions, and 28,470 asserted RDF triples.
The subset has 3 unknown scores and 2 unknown deadlines. These are preserved, not filled with zero.
The activity question is unavailable until the optional activity extension is enabled.

Read docs/questions-and-rules.md for initial questions, follow-up questions, rules, and refusal cases.
Read the numbered explanations below to understand what each command does.

## Structure: the project folders we agreed, with the lab's code logic

```text
kr-oulad/
  README.md
  docs/
    questions-and-rules.md
    data-dictionary.md
    decisions.md
  data/
    raw/                         Original seven CSVs and download manifest
    interim/                     Related rows selected for AAA
    processed/                   Generated oulad.ttl and graph_summary.json
  ontology/education.rdfs.ttl     RDFS schema (not SHACL)
  queries/                       Seven competency-question queries
  src/
    common/pipeline.py           Shared paths and implementation functions
    preparation/
      fetch_data.py
      select_subset.py
      profiling.py
    graph/
      convert_to_rdf.py
      run_queries.py
      rdfs_entailment_demo.py
    learning/                    Later
    access/                      Later
  evaluation/verify.py            CSV/SQL vs RDF reconciliation
  outputs/
    profiling/                   Core HTML, column summaries, rule checks
    answers/                     CSV answers plus availability status
    rdfs/                        Small inferred sample and explanation
    verification.json
  report/                        Recorded execution evidence
  mappings/                      Later
  shapes/                        Later
```

The entry scripts delegate to shared functions so paths, keys, and meanings have one definition.
Read the corresponding function in src/common/pipeline.py when following a stage.

| Course lab pattern | OULAD implementation |
|---|---|
| demos/data/fetch_data.py | src/preparation/fetch_data.py |
| Session 1 profiling.py: pandas + ProfileReport | src/preparation/profiling.py --ydata |
| Session 1 rule_checks.py | quality_checks() in src/common/pipeline.py; rule_checks.csv output |
| Session 2 convert_to_rdf.py: RDFLib, identifiers, typed values | src/graph/convert_to_rdf.py |
| Session 2 run_queries.py | src/graph/run_queries.py and queries/*.rq |
| Session 2 rdfs_entailment_demo.py: owlrl and isolated bad assertion | src/graph/rdfs_entailment_demo.py |

This is a domain adaptation, not a claim that unchanged supply-chain scripts work on education data.

## 0. Activate your lab environment

The installed M2ENV environment was found with pandas, rdflib, owlrl, and ydata_profiling.
Use your own lab environment name if it differs.

```powershell
conda activate M2ENV
Set-Location 'C:\Users\user\OneDrive\Desktop\M2\kr-oulad'
python -c "import sys; print(sys.executable)"
python -c "import pandas, rdflib, owlrl; print('Core dependencies available')"
```

Do not reinstall the environment. The optional HTML profiler uses ydata_profiling,
the same library used in Session 1. The core report is a lightweight pandas report.

## 1. Define the questions

Read docs/questions-and-rules.md. Choose what an answer means before inventing classes.
The first scope is module AAA across its available offerings: enrollments, assessments,
recorded results, registration, and resource metadata. Daily resource activity is optional.
This is a teaching subset, not a representative sample of every OU module.

## 2. Download the original data

```powershell
python src/preparation/fetch_data.py
```

Downloads the ~45 MB UCI ZIP and extracts the seven known CSVs under data/raw/.
The expanded activity file is much larger than the ZIP. The manifest records the source,
license, and SHA-256 hashes. Raw files are never cleaned in place. Existing different
raw files cause an error, not an overwrite.

Manual alternative: download the ZIP from the UCI dataset page listed below, place it at
data/raw/oulad.zip, then run the same command to extract and record checksums.

## 3. Profile the source, then select a connected subset

```powershell
python src/preparation/profiling.py --raw
python src/preparation/select_subset.py --module AAA
python src/preparation/profiling.py
```

The raw profile examines six tables. It excludes the large daily activity CSV.
The UCI copy uses `?` for some missing values. The loader recognizes this marker as unknown
in memory; original raw files are unchanged. Prepared CSVs use empty cells for missing values.
The subset follows foreign keys; it does not independently take the first N rows of every table.
In particular, studentAssessment has no module code: it is selected through assessments.

Inspect outputs/profiling/raw/profile.html and outputs/profiling/subset/profile.html:

- Count rows and columns; examine actual column names (course length is module_presentation_length).
- Review missing percentages, numeric ranges, and duplicate candidate keys.
- Review rule_checks.csv: errors and warnings have different meanings.
- Confirm joins preserve intended records and every reference resolves in the selected scope.
- Write interpretations in docs/decisions.md; do not turn every observed regularity into a universal rule.

For lab-style ydata reports on the selected tables, optionally run:

```powershell
python src/preparation/profiling.py --ydata
```

The lightweight report and ydata reports are complementary: descriptive profiling alone does not check all joins.

## 4. Decide entity identities and relationships

| Table | Row meaning | Entity/key |
|---|---|---|
| courses | One module presentation | CourseOffering: module + presentation; Module: module code |
| studentInfo | One student's participation in one offering | Enrollment: module + presentation + student; Student: student ID |
| studentRegistration | Registration/withdrawal information for that enrollment | Adds facts to the same Enrollment |
| assessments | One assessment in an offering | Assessment: assessment ID |
| studentAssessment | One student's recorded assessment result, potentially banked | AssessmentRecord: student ID + assessment ID |
| vle | Resource metadata within an offering | LearningResource: module + presentation + site ID |
| studentVle | Daily interaction aggregate | DailyInteraction: module + presentation + student + site + day |

All candidate keys are checked before RDF conversion. Nulls do not become the text "nan" or invented zeros.

Relationships:

```text
Student <- hasStudent - Enrollment - inOffering -> CourseOffering - offeringOf -> Module
AssessmentRecord - recordForEnrollment -> Enrollment
AssessmentRecord - forAssessment -> Assessment - assessmentInOffering -> CourseOffering
LearningResource - resourceInOffering -> CourseOffering
DailyInteraction - interactionForEnrollment -> Enrollment
DailyInteraction - withResource -> LearningResource
```

Read ontology/education.rdfs.ttl. Student is a subclass of Person; the three assessment
types are subclasses of Assessment. Domain/range specify entailments, not validation checks.

## 5. Generate RDF facts

```powershell
python src/graph/convert_to_rdf.py
```

Outputs data/processed/oulad.ttl and graph_summary.json. The data file contains asserted facts;
the RDFS vocabulary stays in ontology/education.rdfs.ttl. Numeric values are typed literals,
relative days are signed integers, IDs are stable IRIs, and missing optional values are omitted.

Example only (illustrative IDs, not a claim about a real source record):

```turtle
@prefix edu: <https://example.org/oulad/schema#> .
@prefix id: <https://example.org/oulad/id/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org/oulad/id/student/example-1> a edu:Student .
<https://example.org/oulad/id/enrollment/AAA/2013J/example-1>
    a edu:Enrollment ;
    edu:hasStudent <https://example.org/oulad/id/student/example-1> ;
    edu:inOffering <https://example.org/oulad/id/offering/AAA/2013J> .
```

Do not use student IDs as enrollment IDs: that would merge results from different offerings.
The namespace example.org is a project identifier choice, not an external service to call.

## 6. Ask the questions with SPARQL

```powershell
python src/graph/run_queries.py
```

The runner loads asserted RDF plus the schema. It does NOT silently materialize full RDFS closure.
The assessment query explicitly follows rdfs:subClassOf* so it includes specific assessment types.
Answers are saved under outputs/answers/. In the core build, the early-activity query is explicitly
marked unavailable in status.json, rather than returning a misleading empty answer file.

## 7. See what RDFS actually infers

```powershell
python src/graph/rdfs_entailment_demo.py
```

Read outputs/rdfs/explanation.md and sample_inferred.ttl. The demonstration uses a few real
assessments and students to keep runtime small. It confirms inferred Assessment and Person types.
An isolated deliberately wrong hasStudent assertion demonstrates why domain inference is not validation.
The wrong assertion is never added to the project graph.

RDFS can infer subclasses, superproperties, and subject/object types. It cannot enforce unique keys,
mandatory properties, value ranges, cardinality, or lateness comparisons. Use Python checks now;
translate suitable checks into SHACL later. Follow the explicit distinction in docs/questions-and-rules.md.

## 8. Optional resource-activity extension

```powershell
python src/preparation/select_subset.py --module AAA --activity
python src/preparation/profiling.py
python src/graph/convert_to_rdf.py
python src/graph/run_queries.py
```

The selector streams the large activity CSV in chunks and selects the chosen offerings.
The resulting selected activity is loaded in memory for profiling and RDF; keep the initial module small.
Changing the subset requires rebuilding the profiles, RDF, and query answers in that order.
The manifest controls whether activity is used; an old leftover activity CSV is ignored when disabled.

## Check the conversion

```powershell
python evaluation/verify.py
```

This independently compares CSV-derived counts, late records, low scores, and unknown scores
with RDF/SPARQL results, checks identifier/type counts, and tests the RDFS inference demonstration.

After understanding the individual stages, run the core workflow with `./run-core.ps1`
from your activated Conda terminal. This rebuilds the default AAA core subset, stops if a stage fails,
and does not install packages. Use the individual commands for a different selection or activity extension.

## What comes next

The shapes/, mappings/, src/learning/, and src/access/ directories are reserved for later stages.
There are no trained models, SHACL shapes, R2RML mappings, or natural-language interface yet.
Preserve this historical graph. Later build a separate prediction graph constrained to the chosen
information cutoff; the historical graph includes final outcomes and future events.

## 9. See the graph in Neo4j

This follows the Session 2 neo4j_comparison.py logic: connect with the Neo4j Python driver,
load batches, and ask equivalent questions in Cypher. The OULAD importer reads the already verified
RDF so the two representations share identifiers and values. It never clears the database.

### Start the existing lab service

In PowerShell:

```powershell
docker desktop start
docker compose -f 'C:\Users\user\OneDrive\Desktop\M2\KRR\demos\docker-compose.yml' up -d neo4j
```

Wait until Docker Desktop's engine is running. If `docker desktop` is unavailable, open Docker
Desktop manually and then run the compose command. Do not create a second service on port 7687.

### Load OULAD

From the project folder, with the lab Conda environment active:

```powershell
python src/graph/neo4j_comparison.py
```

The course defaults are bolt://localhost:7687, user `neo4j`, password `kr-labs-pw`, database `neo4j`.
If your existing service has different credentials, set these in the current terminal:

```powershell
$env:NEO4J_URI = 'bolt://localhost:7687'
$env:NEO4J_USER = 'neo4j'
$env:NEO4J_PASSWORD = 'YOUR_EXISTING_PASSWORD'
```

Keep your actual password out of committed files. Do not reset the lab database to fix an authentication error.

### Open and visualize

1. Open http://localhost:7474/browser/ and connect with the same credentials.
2. Paste the following query and click Run.
3. Choose the **Graph** result view. Click nodes to see properties and expand connections.

```cypher
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(s:OULAD:Student)<-[:HAS_STUDENT]-(e:OULAD:Enrollment)-[:IN_OFFERING]->(o:OULAD:CourseOffering)
WHERE e.snapshot=m.activeSnapshot
RETURN p LIMIT 30;
```

Open queries/neo4j.cypher for further graph views: module/offerings/assessments, late records,
low scores, resource descriptions, and optional early activity. Run one query block at a time.
LIMIT keeps the browser readable; it does not limit the imported dataset.

### Representation and verification

- Every imported entity has label OULAD and keeps its RDF IRI as `iri`.
- RDF types become labels, entity links become relationships, and literal values become properties.
- The importer explicitly adds labels inherited through our RDFS subclass hierarchy, such as Assessment
  on a TutorMarkedAssessment. Neo4j itself does not perform RDFS reasoning automatically.
- This is a property-graph view of the data, not a full RDF store: datatype lexical forms and the
  RDFS schema triples are not loaded as separate Neo4j nodes. The authored schema remains in ontology/.
- Identical data/schema imports merge the same snapshot. Changed input creates a separate snapshot;
  the queries select the current verified snapshot through OULADProject. Older snapshots are retained.
- The importer checks node/relationship counts and compares the Cypher late-record count with SPARQL.
  Its result is written to outputs/neo4j/import-summary.json.

Verified Neo4j import on 2026-10-11: **5,037 nodes, 8,221 relationships**, with **815** recorded late
submissions matching the SPARQL result. These totals are for the AAA core subset without daily activity.

To validate the projection without starting a server:

```powershell
python src/graph/neo4j_comparison.py --dry-run
```

Rebuild RDF first and rerun the importer after changing the subset. The core run script does not
automatically start Docker or import Neo4j; this stage is deliberately explicit.

## Sources and reuse

- Official dictionary: https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/
- UCI download/license: https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset
- Dataset citation: Kuzilek, Hlosta, Zdrahal (2017), https://doi.org/10.1038/sdata.2017.171 (CC BY 4.0)
- RDFS semantics: https://www.w3.org/TR/rdf-schema/
- Local course patterns: Session 1 profiling.py; Session 2 RDFLib conversion, SPARQL, and rdfs_entailment_demo.py.

Tested environment: Python 3.12.15, pandas 2.3.3, RDFLib 7.6.0, owlrl 7.6.2,
ydata-profiling 4.18.4. No package installation or version changes were made.

Raw data and generated outputs are gitignored. Commit scripts, schema, queries, docs, and selected
final evidence. Keep secrets out of commits; none are required for the current phase.

