# OULAD knowledge representation project — first working stages

This starter implements download, relational subsetting, profiling, RDF conversion,
RDFS schema, SPARQL questions, RDFS entailment, and a Session 3 OWL ontology with verified inferences.
It reuses the lab techniques and the existing Conda environment; it does not modify the course labs.
No Docker service, API key, LLM, package upgrade, or new environment is needed for the RDF/RDFS core.
The optional Neo4j visualization and Fuseki SPARQL server below use the existing lab Docker services.
For the OWL ontology, terminal reasoner, and results notebook, follow **section 11**. Protégé is not required.

**What is AAA?** An anonymized Social Sciences module with two October offerings (2013J and 2014J).
Our extract has 748 enrollments but 712 distinct student IDs. Read [the AAA explanation](docs/aaa-module.md)
for the offering lengths, assessment schedule, outcomes, and limitations of the anonymized data.

**Project provenance:** Read the [provenance guide](docs/project-provenance.html) for data sources, transformations, modeling choices and verification evidence. An [editable Markdown copy](docs/project-provenance.md) and a [file fingerprint snapshot](docs/provenance-snapshot.json) accompany it.

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
  start-fuseki.ps1                Start lab + project datasets on the same Fuseki server
  docker-compose.fuseki.yml       Project override of the existing lab service
  config/fuseki.ttl               Separate persistent kr and oulad datasets
  docs/
    questions-and-rules.md
    data-dictionary.md
    decisions.md
  data/
    raw/                         Original seven CSVs and download manifest
    interim/                     Related rows selected for AAA
    processed/                   Generated oulad.ttl and graph_summary.json
  ontology/education.rdfs.ttl     RDFS schema (not SHACL)
  ontology/education.owl.ttl      Authored OWL extension for Session 3
  ontology/imports/               Cached FOAF source and reuse/provenance notes
  ontology/exercises/             Deliberately wrong teaching axioms, kept separate
  notebooks/03_ontology_results.ipynb  Executed ontology explanation and results
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
      neo4j_comparison.py
      load_fuseki.py
      prepare_ontology.py
      owl_reasoner.py
      build_ontology_notebook.py
    learning/                    Later
    access/                      Later
  evaluation/verify.py            CSV/SQL vs RDF reconciliation
  evaluation/verify_ontology.py   CSV vs OWL inference and semantic boundary tests
  outputs/
    profiling/                   Core HTML, column summaries, rule checks
    answers/                     CSV answers plus availability status
    rdfs/                        Small inferred sample and explanation
    neo4j/                       Property-graph import evidence
    fuseki/                      Live SPARQL answers and import evidence
    ontology/                    Local imports, reasoning, checks and HTML notebook preview
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
| Session 2 load_fuseki.py: HTTP upload + SPARQL confirmation | src/graph/load_fuseki.py, plus independent answer comparisons |
| Session 3 fetch_ontologies.py: cached imports + small sample | src/graph/prepare_ontology.py and ontology/imports/ |
| Session 3 local_reasoner.py: RDFLib + Owlready2 + HermiT | src/graph/owl_reasoner.py |
| Session 3 check_my_axioms.py and realization demonstrations | evaluation/verify_ontology.py and notebooks/03_ontology_results.ipynb |

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

## 10. Add Fuseki: store and query the RDF online

Fuseki is an RDF database server. It lets you run the same SPARQL questions in a browser or
through an HTTP endpoint. Keep M2ENV for the Python scripts; Docker runs Fuseki independently
of Conda. No new Python environment or package installation is needed for this setup.

```text
CSV -> profiling -> RDF facts + RDFS schema -> RDFLib: local SPARQL
                                         -> Fuseki: served RDF + SPARQL
                                         -> Neo4j: property-graph view + Cypher
```

| Tool | Open in your browser | Query language / connection |
|---|---|---|
| Fuseki | http://localhost:3030/ | SPARQL at http://localhost:3030/oulad/sparql |
| Neo4j | http://localhost:7474/browser/ | Cypher; driver uses bolt://localhost:7687 |

### Start Fuseki with both datasets

Open **PowerShell**, activate the same environment, and run:

```powershell
conda activate M2ENV
Set-Location 'C:\Users\user\OneDrive\Desktop\M2\kr-oulad'
docker desktop start
.\start-fuseki.ps1
```

If Docker Desktop is already running, skip its start command. If that command is unavailable,
open Docker Desktop manually and wait for its engine to be ready. The helper starts only Fuseki;
start Neo4j using section 9 when you also want its graph view.

The helper combines the existing `KRR/demos/docker-compose.yml` with this project's override.
It briefly recreates the Fuseki container if its configuration changed, reuses the existing data
volume and localhost port 3030, and exposes two separate persistent datasets:

- `/kr`: existing course data at `/data/kr` inside the Docker volume.
- `/oulad`: this project's data at `/data/oulad` in that volume.

The course files are unchanged. This lab's admin API rejects dataset creation from the browser,
so the project supplies the dataset definitions at startup using `config/fuseki.ttl`.
No admin account is required to query or load the configured OULAD endpoint locally.

Use `.\start-fuseki.ps1` whenever starting Fuseki for this project. Running the base course Compose
file alone to recreate Fuseki exposes only `/kr`; the OULAD data stays in the volume, and rerunning
the helper exposes it again. Do not remove the Docker data volume to troubleshoot a missing dataset.

If the course folder moves, pass its actual Compose path:

```powershell
.\start-fuseki.ps1 -LabCompose 'D:\courses\KRR\demos\docker-compose.yml'
```

### Load the facts and schema

After generating RDF in step 5:

```powershell
python src/graph/load_fuseki.py
```

The loader combines `data/processed/oulad.ttl` and `ontology/education.rdfs.ttl` into the
**default graph of `/oulad`**. This allows the existing `queries/*.rq` files to work unchanged.
The AAA core build is expected to contain 28,470 data triples plus 105 schema triples: **28,575 total**.
These are triples, not the number of visual nodes in Neo4j.

Rerunning an identical import leaves the graph as it is. When input changes, the loader saves the
previous nonempty default graph under `outputs/fuseki/backups/`, then replaces that default graph.
The loader targets `/oulad` only; it does not update `/kr` or any named graph.
Treat `/oulad`'s default graph as the generated project snapshot: manual additions there will be
included in a backup and replaced on the next load.

### Open Fuseki and run SPARQL

1. Open http://localhost:3030/.
2. Select dataset **`/oulad`**, then open its **Query** page.
3. Paste this query and run it:

```sparql
PREFIX edu: <https://example.org/oulad/schema#>

SELECT ?student ?enrollment ?offering
WHERE {
  ?enrollment a edu:Enrollment ;
              edu:hasStudent ?student ;
              edu:inOffering ?offering .
}
ORDER BY ?offering ?student
LIMIT 30
```

This shows students connected to their enrollments and offerings as a result table. For the
interactive node-and-edge view, continue using Neo4j's Graph view in section 9.

To count all loaded triples:

```sparql
SELECT (COUNT(*) AS ?triples)
WHERE { ?s ?p ?o }
```

For the full competency questions, open a `.rq` file from `queries/`, copy its contents into
the Query page, and run it. For example, `03_late_records.rq` returns 815 recorded late submissions
for the core subset, excluding banked records and records without known deadlines.
Use **SPARQL** in Fuseki; the commands in `queries/neo4j.cypher` belong in Neo4j.

### Verify and reload after changes

Every load checks the stored graph and compares all available query answers with RDFLib,
including the returned rows rather than just their counts. Results are saved as CSVs under
`outputs/fuseki/`; `import-summary.json` records the counts, source hashes, and verification status.
Question 7 stays marked unavailable until you rebuild with the activity extension.

To verify an already loaded graph without changing the database:

```powershell
python src/graph/load_fuseki.py --check-only
```

Verified on **2026-10-12** with the existing M2ENV and Fuseki 5.5.0: 28,575 triples;
all six core query answers match RDFLib; a repeat import leaves the graph unchanged.
Both datasets survived a container restart. The lab's `/kr` dataset still has 135,841 triples.

After changing the subset, rebuild RDF and rerun the loader. `run-core.ps1` does not start Docker
or load either database automatically.

Loading an RDFS schema does **not** enable automatic RDFS inference. This Fuseki configuration
stores the supplied triples; query 2 explicitly follows the subclass hierarchy with a property
path. The separate RDFS inference demonstration remains step 7.

If you get a connection error, check Docker Desktop and run the helper again. If `/oulad` is missing,
use the helper rather than uploading into `/kr`. The SPARQL endpoint is
`http://localhost:3030/oulad/sparql`; the Graph Store upload endpoint is
`http://localhost:3030/oulad/data?default`.

See Apache Jena's [Fuseki configuration documentation](https://jena.apache.org/documentation/fuseki2/fuseki-configuration.html)
for dataset definitions and [SPARQL over HTTP documentation](https://jena.apache.org/documentation/fuseki2/soh.html)
for query and graph-upload protocols.

## 11. Session 3: build, reason over, and explain the OWL ontology

This stage follows the Session 3 method using OULAD: begin with questions, state precise definitions,
reuse suitable published terms, infer classifications, and investigate contradictory axioms.
Everything runs through Python and Java in your current setup. **No Protégé or Docker is needed.**

### What you now have

| Layer | Meaning in this project | File |
|---|---|---|
| RDF facts, or ABox | Real student, enrollment, assessment and score assertions | `data/processed/oulad.ttl` |
| RDFS schema | Existing hierarchy, properties, domains and ranges | `ontology/education.rdfs.ttl` |
| OWL definitions, or TBox | Defined classes, disjointness, cardinality, inverse and functional properties | `ontology/education.owl.ttl` plus its local imports |
| Reasoner | HermiT computes consistency, class hierarchy and individual classifications | `src/graph/owl_reasoner.py` |
| Inferred results | New named class memberships derived from the facts and definitions | `outputs/ontology/inferred-types-full.ttl` |
| Evidence | Reconciliation with CSVs and tests of OWL semantics | `outputs/ontology/verification.json` |
| Explanation | Executed tables, relationship diagram, examples and local SPARQL | `notebooks/03_ontology_results.ipynb` |

An OWL ontology is still RDF and can be stored as Turtle (`.ttl`). Changing the filename to `.owl`
does not create an ontology: the actual OWL axioms are what add meaning. The extension retains
the same `edu:` IRIs as your RDF, so the definitions refer to the entities you already created.

### Run the stage, in order

First complete the core RDF steps if `data/processed/oulad.ttl` is missing. Then, in PowerShell:

```powershell
conda activate M2ENV
Set-Location 'C:\Users\user\OneDrive\Desktop\M2\kr-oulad'

# 1. Prepare OWL declarations, locally resolved imports, and a small real-data sample.
python src/graph/prepare_ontology.py

# 2. First check the small sample and inspect its inferred types.
python src/graph/owl_reasoner.py

# 3. Check all current OULAD facts against the ontology.
python src/graph/owl_reasoner.py --full-data

# 4. Compare inferred individuals with the selected CSVs and test Session 3 semantics.
python evaluation/verify_ontology.py

# 5. Build and execute the explanation notebook, and export a browser-readable HTML copy.
python src/graph/build_ontology_notebook.py
```

Stop if a command fails. Full-data reasoning can take several minutes; wait for its consistency
and inference summary before running verification. HermiT uses Java, not a remote service.
The existing M2ENV already supplies RDFLib, Owlready2, pandas and the notebook libraries;
JDK 21 is already installed. No environment or package changes were made.

After the first successful run, **viewing the notebook or HTML does not require rerunning HermiT**.
Rerun the stage when the source facts or ontology change. The notebook checks recorded source
hashes and refuses to present results for changed source files as current.

### Open the results

- Open `notebooks/03_ontology_results.ipynb` in VS Code or Jupyter. Select **M2ENV** as the Python
  environment/kernel if you want to rerun its cells. The notebook is delivered with executed outputs.
- For a simple browser view, open `outputs/ontology/ontology-results.html`.
- For machine-readable evidence, inspect `outputs/ontology/inferred-class-counts.csv`,
  `reasoned-full.json`, and `verification.json`.

The notebook contains the domain relationship diagram, inferred class hierarchy, six class counts,
real examples showing the supporting facts, a before/after SPARQL comparison, the teaching sample,
and the semantic test results. Its queries run in local RDFLib graphs; they do not change Fuseki.

### The six new definitions and the questions they answer

| New class | Definition in plain language | Question | Verified AAA count |
|---|---|---|---:|
| `SuccessfulEnrollment` | Enrollment with final result Pass or Distinction | Which enrollments succeeded? | 531 |
| `WithdrawnEnrollment` | Enrollment with final result Withdrawn | Which enrollments ended in withdrawal? | 126 |
| `LowScoreAssessmentRecord` | AssessmentRecord with a known score strictly below 40 | Which recorded results are low? | 90 |
| `BankedAssessmentRecord` | AssessmentRecord with `isBanked = true` | Which results were carried forward? | 42 |
| `NonBankedAssessmentRecord` | AssessmentRecord with `isBanked = false` | Which results were not carried forward? | 3,107 |
| `EnrollmentWithLowScore` | Enrollment with at least one LowScoreAssessmentRecord | Which enrollments have a low result? | 75 |

These count named IRIs in the loaded data, not triples or a proof that every pair denotes different
real-world entities. In particular, 90 low-score records belong to
75 enrollments. The definitions describe historical facts. They are neither predictions nor
evidence that one low score causes a final failure.

Each base and derived class has an `edu:answersCQ` annotation explaining why it is in the model.
For readability, the following uses Manchester-style class expressions:

```text
SuccessfulEnrollment EquivalentTo:
    Enrollment and (finalResult value "Pass" or finalResult value "Distinction")

LowScoreAssessmentRecord EquivalentTo:
    AssessmentRecord and (score some xsd:decimal[< 40])

EnrollmentWithLowScore EquivalentTo:
    Enrollment and (hasAssessmentRecord some LowScoreAssessmentRecord)
```

`EquivalentTo` supplies both directions: the class has the stated meaning, and an individual
meeting that meaning can be classified into the class. Replacing it with `SubClassOf` gives
only a necessary condition. The automated test makes that change in memory and confirms that
the successful enrollments are no longer inferred from their outcomes.

### The other modeling decisions

1. **Explicit property kinds.** The preparation script translates the existing RDFS declarations
   into OWL classes, object properties for entity links, and datatype properties for literals.
   The original RDFS file remains the source for those shared declarations.
2. **A person is not an enrollment.** Person, Module, CourseOffering, Enrollment, Assessment,
   AssessmentRecord, LearningResource and DailyInteraction are modeled as pairwise disjoint.
   Student remains a subclass of Person. The three assessment subtypes are also disjoint.
   These are project modeling commitments, not discoveries automatically made from the CSVs.
3. **One enrollment concerns one student and one offering.** OWL uses qualified `exactly 1`
   restrictions on `hasStudent` and `inOffering`. With their ranges, these identify one filler
   per relationship. This does not enforce an explicit required field in the RDF file.
4. **Relationships can be read in reverse.** `hasAssessmentRecord` is declared inverse to
   `recordForEnrollment`. HermiT uses this when finding enrollments with a low-score record.
5. **Contextual values are single-valued.** `finalResult`, `score`, and `isBanked` are functional
   datatype properties. For example, two distinct final-result strings for the same enrollment
   conflict with this model. Final result is attached to Enrollment, not timeless Student.
6. **Use the appropriate reasoner.** The ontology contains inverse properties, unions,
   datatype restrictions and exact cardinality. Use the supplied HermiT workflow; an EL-only
   reasoner is not sufficient to check all these constructs. A successful run is not being
   presented as a separate formal OWL-profile conformance audit.

### Published ontology reuse

The lab uses supply-chain vocabularies; this education project reuses **FOAF Person and Agent**.
The preparation script extracts a small documented fragment from the unchanged cached official
`ontology/imports/foaf.rdf`, keeping the published IRIs. The mapping is:

```text
edu:Student -> edu:Person -> foaf:Person -> foaf:Agent
```

The arrows here mean subclass. All **712 distinct Student individuals** consequently receive
the FOAF Person type. We do not declare our Student class equivalent to all people.

The selected fragment contains class declarations, source labels/comments, and the Person-to-Agent
subclass axiom. **It is not a complete FOAF import or a complete BFO alignment.** Read
`ontology/imports/README.md` for the source URL, SHA-256, authors, license, and omissions.
The workspace catalog maps import IRIs to local files, following the same pattern as the lab.
Once the supplied snapshot is present, the preparation and reasoning steps need no network.

### What the tests establish

The full AAA graph was checked, not only the sample. HermiT found the clean ontology plus data
consistent and found no unsatisfiable named classes. The run produced **6,119 new named type
assertions** for the current core dataset. The CSV reconciliation checks compare exact individual
identities, not only totals. Expected result: **17/17 checks passed**.

The small sample is deliberately selected: **7 enrollments, 51 individuals, 279 source triples**.
It includes each outcome plus low, banked and unknown-score cases. Identifiers and facts are real;
readable labels and explicit individual declarations are added for display. The selection reasons
are recorded in `outputs/ontology/preparation.json`.

Additional synthetic tests demonstrate the important Session 3 distinctions:

| Example | Expected reasoning result | Meaning |
|---|---|---|
| Known score 39, 40, 41, and an unknown score | Only 39 is inferred low | Strict boundary; unknown is not zero |
| Enrollment without explicit student/offering links | Consistent | OWL can satisfy the restriction with unstated fillers |
| Two student IRIs on one enrollment | Can be consistent | Different names can denote the same person |
| The same two students asserted `differentFrom` | Inconsistent | Exactly one cannot hold for two distinct fillers |
| `only` low-score records | Does not entail a record exists | Universal restriction is not an existence claim |
| `some` and `only` low-score records | Entails a low-score record exists | Existential restriction adds existence |
| SuccessfulEnrollment changed to `SubClassOf` only | No successful membership inferred from outcome alone | Necessary condition is not a full definition |

### The deliberate error from the lab, adapted to OULAD

`ontology/exercises/domain-error.ttl` contains two intentionally impossible classes. Both misuse
`hasStudent` on a Student. The property has domain Enrollment, so this also makes the subject an
Enrollment. Student implies Person, and Person is disjoint from Enrollment: the class cannot have
an instance. One class uses `some`; the other uses `exactly 1`, reflecting the lab's expressivity lesson.

An ontology with those empty impossible classes can still be consistent. The generated
`domain-inconsistent.ttl` asserts a fictional instance of one impossible class, making the entire
example inconsistent. `verify_ontology.py` expects both outcomes. These teaching axioms are never
mixed into the real RDF, the clean OWL ontology, Fuseki, or Neo4j.

To inspect their reports individually, optionally run:

```powershell
python src/graph/owl_reasoner.py outputs/ontology/workspace/domain-error.ttl
python src/graph/owl_reasoner.py outputs/ontology/workspace/domain-inconsistent.ttl
```

These commands intentionally return a nonzero exit status because their inputs contain the
documented errors. The clean workflow above should return success at every step.

### What remains SPARQL or validation

- **Late submission:** comparing `submissionDay > deadlineDay` across a record and assessment
  remains in `queries/03_late_records.rq`. OWL datatype facets compare a value with a fixed bound;
  they do not implement this comparison between two property values.
- **Unknown score:** the existing SPARQL absence query describes the loaded extract. We do not
  invent an OWL MissingScore type from a missing triple.
- **Mandatory fields, keys and source ranges:** keep the existing Python quality checks;
  Session 4 SHACL is the next step for explicit graph validation.
- **Database use:** the current Fuseki and Neo4j loaders still use their original RDF/RDFS inputs.
  Merely uploading an OWL file to Fuseki would not run HermiT. This stage exports additional named
  type assertions separately and demonstrates queries over facts plus those types in the notebook.
  The export is not the complete OWL deductive closure: it omits anonymous fillers and inferred
  property assertions, among other consequences.

### Which files should you edit?

Edit shared class/property declarations in `ontology/education.rdfs.ttl`, and OWL definitions in
`ontology/education.owl.ttl`. Then rerun preparation, reasoning and verification. The files in
`outputs/ontology/workspace/` are generated copies and local imports. The notebook builder also
rewrites `notebooks/03_ontology_results.ipynb`; save personal notebook experiments under another name.

This extension adapts the existing course patterns in
`KRR/demos/session-03-ontology/local_reasoner.py`, `check_my_axioms.py`, and `realize_sample.py`.
It uses the same RDFLib/Owlready2/HermiT approach with OULAD identifiers, local imports and
independent CSV checks. Course source files remain unchanged.

Further reference: [OWL 2 Primer](https://www.w3.org/TR/owl2-primer/) and
[FOAF specification](https://xmlns.com/foaf/spec/).

## Sources and reuse

- Official dictionary: https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/
- UCI download/license: https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset
- Dataset citation: Kuzilek, Hlosta, Zdrahal (2017), https://doi.org/10.1038/sdata.2017.171 (CC BY 4.0)
- RDFS semantics: https://www.w3.org/TR/rdf-schema/
- Local course patterns: Session 1 profiling.py; Session 2 RDFLib conversion, SPARQL, and rdfs_entailment_demo.py.

Tested environment: Python 3.12.15, pandas 2.3.3, RDFLib 7.6.0, owlrl 7.6.2,
ydata-profiling 4.18.4. No package installation or version changes were made.

Raw data are gitignored; generated evidence is organized under outputs/. Commit scripts, schema,
queries, docs, and selected final evidence. Keep secrets out of commits.

