# OULAD knowledge representation project

This starter implements download, relational subsetting, profiling, RDF conversion,
RDFS schema, SPARQL questions, RDFS entailment, and a Session 3 OWL ontology with verified inferences.
It reuses the lab techniques and the existing Conda environment; it does not modify the course labs.
No Docker service, API key, LLM, package upgrade, or new environment is needed for the RDF/RDFS core.
The optional Neo4j visualization and Fuseki SPARQL server below use the existing lab Docker services.
For the OWL ontology, terminal reasoner, and results notebook, follow **section 11**. Protégé is not required.
For SHACL graph validation, triage, the gate and run provenance, follow **section 12**.
For PostgreSQL, R2RML mappings, materialization and Ontop virtualization, follow **section 13**.
For learning, count baselines and detailed model evaluation, follow **section 14**.
For natural-language questions, query checking and the local interface, follow **section 15**.

**What is AAA?** An anonymized Social Sciences module with two October offerings (2013J and 2014J).
Our extract has 748 enrollments but 712 distinct student IDs. Read [the AAA explanation](docs/aaa-module.md)
for the offering lengths, assessment schedule, outcomes, and limitations of the anonymized data.

**Project provenance:** Read the [provenance guide](docs/project-provenance.html) for data sources, transformations, modeling choices and verification evidence. An [editable Markdown copy](docs/project-provenance.md) and a [file fingerprint snapshot](docs/provenance-snapshot.json) accompany it.

**Understand the project:** Read the [detailed walkthrough](docs/project-walkthrough.html) for what we built, result interpretation, documented challenges, actual fixes and deliberate teaching errors. An [editable version](docs/project-walkthrough.md) is included.

## Run it, step by step

Open an Anaconda Prompt or a PowerShell terminal configured for Conda. Run from the project root.

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'

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

# 6. Validate the asserted graph. Warnings are visible; violations stop the gate.
python src/validation/validate.py

# 7. Run the competency questions.
python src/graph/run_queries.py

# 8. Demonstrate RDFS inference on a small real-data sample.
python src/graph/rdfs_entailment_demo.py

# 9. Compare CSV/SQL answers with RDF/SPARQL answers.
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
    validation/                  SHACL validator, examples and provenance query
    learning/                    Session 6 models, leakage checks and evaluation
    access/                      Session 7 natural-language questions and SPARQL
  run-shacl.ps1                  Complete Session 4 demonstration
  evaluation/verify_shacl.py      Graph fault tests and full CSV warning reconciliation
  evaluation/fixtures/shacl/      Real and deliberately broken samples for CI
  .github/workflows/shacl-gate.yml  Local workflow definition for the repository
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
  mappings/oulad-mapping.ttl      Shared Session 5 R2RML mapping
  src/integration/               PostgreSQL, materialization, virtualization and provenance
  run-integration.ps1            Complete Session 5 workflow
  outputs/integration/           Unique run folders, comparisons and reports
  shapes/oulad-shapes.ttl         Session 4 graph validation policies
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
Set-Location 'D:\DESKTOP\M2\kr-oulad'
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
validate the mapped graph with the Session 4 SHACL shapes in section 12. Follow the explicit distinction in docs/questions-and-rules.md.

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

Session 6 learning is implemented in src/learning/. The src/access/ directory is reserved for a later stage.
SHACL validation is implemented in section 12; PostgreSQL, R2RML mapping and Ontop integration are implemented in section 13. Session 6 models and evaluation are implemented in section 14; Session 7 adds the natural-language interface in section 15.
Preserve the historical graph. Session 6 builds a separate learning graph constrained to day 60;
the historical graph includes final outcomes and later events that must stay outside model inputs.

## 9. See the graph in Neo4j

This follows the Session 2 neo4j_comparison.py logic: connect with the Neo4j Python driver,
load batches, and ask equivalent questions in Cypher. The OULAD importer reads the already verified
RDF so the two representations share identifiers and values. It never clears the database.

### Start the existing lab service

In PowerShell:

```powershell
docker desktop start
docker compose -f 'D:\DESKTOP\M2\KRR\demos\docker-compose.yml' up -d neo4j
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
Set-Location 'D:\DESKTOP\M2\kr-oulad'
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
Set-Location 'D:\DESKTOP\M2\kr-oulad'

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
  Session 4 SHACL now validates the explicit graph requirements; follow section 12.
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

## 12. Session 4 — SHACL validation, triage and gate

Session 3 asks **what the ontology entails**. Session 4 asks **whether the supplied graph meets explicit requirements**. For example, OWL's open-world semantics can allow an enrollment whose Student link is not stated; a SHACL `sh:minCount 1` check flags that missing link. SHACL does not repair the graph or run the OWL reasoner.

This extension follows `KRR/demos/session-04-shacl/validate.py`, the triaged Brunel shapes and the lab's good/broken sample pattern. The lab files were available locally; no additional PDF is needed. The existing **M2ENV** already contains **pySHACL 0.40.1** and **RDFLib 7.6.0**. No environment replacement or package upgrade was needed.

### Step 1 — activate the existing environment

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
python -c "import pyshacl, rdflib; print(pyshacl.__version__, rdflib.__version__)"
```

On another machine only, if pySHACL is missing, install the lab version in the already activated environment with `python -m pip install pyshacl==0.40.1`. Do not create another environment just for SHACL.

### Step 2 — prepare the asserted RDF if needed

The current working copy already contains `data/processed/oulad.ttl`. If rebuilding from the selected CSVs:

```powershell
python src/graph/convert_to_rdf.py
```

The validator reads this file plus `ontology/education.rdfs.ttl` and `shapes/oulad-shapes.ttl`. It uses the class hierarchy for SHACL class checks but keeps inference set to `none`. It does not load the OWL inferred types or the deliberate ontology-error files. Neither Neo4j nor Fuseki has to be running.

### Step 3 — validate the full graph

```powershell
python src/validation/validate.py
```

Allow several minutes for the full graph; the cross-record SPARQL constraints are slower than core constraints. First read the printed **focus-node counts**. Expected structural coverage for the current AAA build: 712 Students, 748 Enrollments, 2 Offerings, 1 Module, 12 Assessments, 3,149 AssessmentRecords and 413 LearningResources. All 14 target-bearing shapes are reported; only optional activity has zero nodes.

Expected current result: **0 Violations, 5 Warnings, strict SHACL conforms False, GATE PASS, exit code 0**. The warnings are three unknown scores and two unknown exam deadlines. The existing facts are retained.

Open [the full validation report](outputs/shacl/full/report.html). Each run writes:

| File under `outputs/shacl/full/` | Purpose |
|---|---|
| `report.html` | Readable results, focus counts and input fingerprints |
| `report.ttl` | Standard SHACL validation report |
| `report.txt` | pySHACL's detailed text report |
| `results.csv` | One row per result, including focus, path, severity and message |
| `summary.json` | Gate decision, strict conformance, run ID, versions, timestamps and hashes |
| `provenance.ttl` | PROV-O record of this actual validation activity and its inputs/outputs |

Strict conformance and the project gate answer different questions. With these validator settings, warnings make SHACL conformance false, but the gate permits documented warnings. **Exit 1** blocks on violations, unknown severities or empty required targets. **Exit 2** means a parsing, dependency, shape or execution error. Neither should be treated as success.

### Step 4 — build the small real-data and broken examples

```powershell
python src/validation/prepare_examples.py
python src/validation/validate.py --data evaluation/fixtures/shacl/valid.ttl --out outputs/shacl/sample
python src/validation/validate.py --data evaluation/fixtures/shacl/broken.ttl --out outputs/shacl/broken
```

The valid example has 299 unchanged source triples and seven selected enrollments. It should give **0 Violations, 3 Warnings and gate PASS**. The broken example changes one Student link to an untyped identifier. It should give **1 Violation, 3 Warnings and gate FAIL (exit 1)**. That last failure is intentional. Real data are not changed.

`evaluation/fixtures/shacl/selection.json` records the selected enrollments, source fingerprint, fixture fingerprints and exact changed triple. The fixtures are stored outside the ignored `data/` folder so they can be committed and used by CI without downloading OULAD.

### Step 5 — see why triage matters

```powershell
python src/validation/validate.py --data evaluation/fixtures/shacl/valid.ttl --shapes outputs/shacl/examples/oulad-shapes-v0.ttl --out outputs/shacl/draft
```

This intentionally naive draft treats unknown scores and deadlines as blocking errors. Expect **3 Violations, 0 Warnings, gate FAIL (exit 1)** on the small sample. Compare it with the sample report from Step 4: the same three absences become visible warnings after reviewing source completeness. We change the policy, not the data.

Read [SHACL rules and triage decisions](docs/shacl-triage.md) for rule coverage, the five actual warning identities, and why missing is not zero. Late submissions and low scores are observed events, not automatic data-quality violations. Studied credits and resource week ranges are not mapped to RDF, so their checks stay in Python profiling.

### Step 6 — verify that good and bad cases behave correctly

```powershell
python evaluation/verify_shacl.py
```

Run this after a full validation with the current shapes and validator. It checks real sample fidelity, source-versus-target counts, exact warning identities against CSVs, score boundaries, required links, wrong datatypes, key duplicates, cross-offering links, signed dates, optional activity and the zero-focus trap. It also rejects stale full-run fingerprints. See `outputs/shacl/verification.json` for the recorded checks.

For a quick run requiring only the committed fixture and schema:

```powershell
python evaluation/verify_shacl.py --sample-only
```

This writes `outputs/shacl/verification-sample.json`. The full CSV reconciliation is deliberately omitted in this mode.

### Step 7 — run the complete Session 4 demonstration

Instead of repeating Steps 3–6 manually:

```powershell
.\run-shacl.ps1
```

The helper prepares the examples, validates the full graph and both fixtures, runs the draft, and verifies the results. It explicitly expects exit 1 for the two deliberate failure demonstrations and stops on any unexpected exit code. The main `run-core.ps1` now also runs the **full SHACL gate immediately after RDF conversion**, before answering questions.

### Step 8 — understand the automatic gate and CI status

**Your GitHub screenshot shows the SHACL workflow succeeded** at commit `afd8535` on `main` (34 seconds total; validate job 29 seconds). This is screenshot evidence supplied by you; no run URL or independent API check is recorded. The new Session 5 integration workflow has a separate pending remote status.

| Run | What it covers | Status |
|---|---|---|
| Full local verification | 37 checks, including full CSV/report/provenance comparisons | Saved 15 October result: all passed |
| GitHub Actions workflow | Validate the real fixture, run 31 shared checks with `--sample-only`, and require exit 1 from the deliberately broken fixture | Success shown in your screenshot at `afd8535`; URL not supplied |

The workflow is [`.github/workflows/shacl-gate.yml`](.github/workflows/shacl-gate.yml), named **OULAD SHACL gate**, with job ID `validate`. It runs on pushes and pull requests affecting the listed SHACL paths, and supports a manual trigger. README-only changes do not trigger it automatically. It uses Python 3.12, pySHACL 0.40.1 and RDFLib 7.6.0 on an Ubuntu runner; your local Conda environment is unchanged.

To run the same 31-check verification locally, from the project root in M2ENV:

```powershell
python evaluation/verify_shacl.py --sample-only
```

That writes `outputs/shacl/verification-sample.json`. It is a local check, not a GitHub run. The six extra full-data checks remain local because the raw data are gitignored; the fixtures can be committed without downloading OULAD on the runner.

For remote execution, commit the workflow and its shapes, RDFS schema, validation scripts, verifier and fixture files, then push to the intended repository with Actions enabled. Once the workflow is on the default branch, you can also select **Actions → OULAD SHACL gate → Run workflow**. Retain the run URL, commit SHA and result as evidence. This documentation update did not commit, push or run GitHub Actions.

Making a failure block merging requires a separate branch-protection/ruleset setting. Before requiring this workflow for every pull request, adjust its workflow-level path filters so unrelated changes do not leave the required check pending. See [GitHub's explanation](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks). No merge protection was configured by this task.

The [provenance guide's SHACL and CI section](docs/project-provenance.html#shacl-and-ci-what-is-implemented-and-what-has-run) explains the exact checks, expected failures and recorded CI evidence. The present workflow does not upload report artifacts; inspect its logs for the run result.

### Step 9 — inspect provenance and maintain the shapes

The [project provenance guide](docs/project-provenance.html) now includes Session 4. Unlike the earlier file-level narrative alone, each SHACL run also creates a machine-readable provenance record for the actual validation activity. Its data, schema and shapes entities have SHA-256 identifiers, and its software agent identifies the validator code/version.

To inspect the run record locally without a server:

```powershell
python src/validation/show_provenance.py
```

Edit `shapes/oulad-shapes.ttl` to change policies. Rerun the full validator and `verify_shacl.py`; regenerate the examples when their source data or draft shapes change. Reports within each output folder are overwritten on rerun, so copy a folder first if retaining that previous run matters. Update the dated guide observations when the scope or expected counts change.

The shapes use **SHACL Core** for cardinality, datatype, vocabulary, ranges, forbidden fields and same-node date order. They use **SHACL-SPARQL** where a rule compares different records or linked paths. They add no new RDF facts and do not alter the OWL ontology or database imports.

References: [W3C SHACL](https://www.w3.org/TR/shacl/), [pySHACL](https://github.com/RDFLib/pySHACL), [W3C PROV-O](https://www.w3.org/TR/prov-o/).


## 13. Session 5 — PostgreSQL, mappings, materialization and virtualization

The same six AAA CSV tables now feed PostgreSQL. One R2RML mapping describes how their rows become the existing RDF identifiers and properties. **Morph-KGC executes it to save an RDF snapshot; Ontop uses it to translate SPARQL into SQL at query time.** Both are checked against the original RDF and independent SQL answers.

### Step 1 — keep M2ENV and check prerequisites

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
python -c "import morph_kgc, psycopg2, sqlalchemy, rdflib, pyshacl; print('Integration packages available')"
java -version
docker info
```

Java 21 and Docker Desktop must be available. This working copy already has the tested packages; Morph-KGC 2.10.0 was added to **the existing M2ENV**, using its existing dependencies. No second Conda environment is needed. If Docker is stopped, start Docker Desktop and wait for its engine.

For a fresh installation only, first review `requirements-integration.txt`, then install the tested integration dependencies and Morph separately:

```powershell
python -m pip install -r requirements-integration.txt
python -m pip install --no-deps morph-kgc==2.10.0
```

Why `--no-deps`? Morph-KGC 2.10.0 declares older RDFLib/PyOxigraph upper bounds than the lab environment. The course uses this explicit compatibility override; our real mapping and query tests verify the combination used here. This is a project-tested configuration, not a claim that Morph supports every newer dependency or every feature. A global `pip check` may still report those declared-bound conflicts. Do not rerun the install commands merely to start the project.

### Step 2 — check the prepared input

The full mode expects `data/interim/` with the six AAA CSVs and `data/processed/oulad.ttl` from the core pipeline. If starting from an empty clone, follow the earlier download, selection and RDF steps first. The small fixture mode below needs no raw download. The integration intentionally excludes `studentVle` activity and expects the existing default AAA scope.

### Step 3 — run the complete extension

```powershell
.\run-integration.ps1
```

The helper creates `.env.integration` once with a generated local password, starts the project PostgreSQL container, prepares the pinned Ontop/JDBC downloads, and runs the complete verification. Existing credentials are reused. It stops at the first failed step. Read **`outputs/integration/integration-results.html`** afterward.

Equivalent individual steps, useful for learning or diagnosing a failure:

```powershell
python src/integration/init_config.py
docker compose --env-file .env.integration -f docker-compose.postgres.yml up -d --wait
python src/integration/setup_ontop.py
python evaluation/verify_integration.py
```

The verifier loads the database, materializes, queries, compares, validates with SHACL, runs the change experiment and records provenance. It replaces only the six managed tables in its selected schema, in a transaction. Treat these as reproducible project tables: manual edits there are replaced on the next full run. Original CSVs and the original RDF file are retained.

The database is **127.0.0.1:5433**, database `oulad`, schema `oulad`, user `oulad`; its password is in `.env.integration`. A PostgreSQL client such as pgAdmin or DBeaver can use those values. The container internally uses port 5432. This separate Compose project and persistent volume avoid changing the course's existing services. Environment variables override the connection file when connecting to an existing PostgreSQL server. Use an explicitly dedicated schema because loading replaces its managed tables.

For a faster complete test on a small connected dataset:

```powershell
.\run-integration.ps1 -Fixture
```

It uses `oulad_fixture` and a separate demo schema, writes `outputs/integration/fixture-results.html`, and expects 299 triples, 23 passed checks and three SHACL warnings. It does not replace the full `oulad` tables.

### Step 4 — understand the files and the mapping

```text
config/postgres/schema.sql             Six tables, keys, constraints and mapping views
config/postgres/connection.env.example Connection field reference; no real password
docker-compose.postgres.yml            Dedicated local PostgreSQL service
mappings/oulad-mapping.ttl              Shared R2RML mapping for both engines
src/integration/load_database.py       Transactional CSV loader and load receipt
src/integration/materialize.py         PostgreSQL → saved asserted RDF
src/integration/run_ontop.py            SPARQL → SQL → live PostgreSQL results
src/integration/compare.py             Graph terms and answer multiset comparison
src/integration/freshness.py           Separate-schema update experiment
src/integration/provenance.py          Run inputs, database state and output fingerprints
queries/integration/                  Portable assessment query and six SQL equivalents
evaluation/verify_integration.py       Complete integration verification
evaluation/fixtures/integration/       Small real-data CSVs and expected RDF, with attribution
.github/workflows/integration.yml      Small-dataset integration CI
outputs/integration/runs/<run-id>/      Retained results for each execution
```

In R2RML, `rr:logicalTable` supplies rows, `rr:subjectMap` builds each resource IRI, and `rr:predicateObjectMap` adds a relationship or typed value. For example, an enrollment is identified by **module + presentation + student**, never student ID alone. Joins in the views reconstruct each assessment record's offering and enrollment. Decimal scores remain decimal; signed relative dates remain integers; SQL NULL produces no score/deadline fact.

The `KnownScores` mapping explicitly filters `WHERE score IS NOT NULL`. During testing Morph emitted an invalid `"None"^^xsd:decimal` for an unfiltered nullable score. The separate score mapping fixes that problem without removing the assessment record. The exact graph comparison guards against its return.

### Step 5 — run individual queries and inspect generated SQL

After the database is loaded:

```powershell
python src/integration/run_ontop.py --query queries/01_enrollments.rq
python src/integration/run_ontop.py --query queries/integration/02_assessments.rq
python src/integration/run_ontop.py --query queries/03_late_records.rq
python src/integration/materialize.py --out outputs/integration/manual-materialization
```

Individual query outputs go to `outputs/integration/manual-virtual/`: `.csv` answers, `.sql.txt` generated SQL, a diagnostic `.log`, and `.json` metadata. The last command writes `oulad-mapped.nt`, a new RDF snapshot. These manual folders are overwritten on another manual run; the complete verifier uses unique run folders.

The six tested questions are enrollment counts per offering, assessment details, late records, scores below 40, outcome counts, and unknown scores. Question 2 uses the explicit current assessment types (`TMA`, `CMA`, `Exam`) in `queries/integration/02_assessments.rq`; the original local query follows the RDFS subclass hierarchy. Their answers are compared. Extend that portable query if new assessment subclasses are introduced.

No OWL file is supplied to Ontop for this baseline. This demonstrates mapping virtualization over asserted facts; it does not repeat HermiT's full OWL classifications. “Materialization” here means generating mapped RDF, distinct from the earlier materialization of inferred types.

### Step 6 — interpret the result

The full run checks **28,470 mapped triples**, all six answer multisets and **23 integration checks**. The mapped graph passes the existing SHACL gate with **0 violations and 5 warnings** (three unknown scores, two unknown deadlines). Strict SHACL conformance can remain false under that warning policy. The integration count is separate from Session 4's 37 regression checks.

The freshness experiment copies the input to `oulad_demo`, changes one low score to 99 and commits. Ontop's low-score count changes **90 → 89**; the old RDF snapshot stays **90**; a new materialization returns **89**. The score is restored and the demo database fingerprint is checked. The full `oulad` schema is unchanged by this experiment. Fixture mode demonstrates **2 → 1** instead.

Each run folder contains `summary.json`, `report.html`, `load.json`, `graph-comparison.json`, the mapped graph, answer files, generated SQL, a `shacl/` report, `freshness/` evidence, `provenance.ttl` and `provenance-check.json`. `latest-full.json` points to the latest successful full run. Failed runs keep `failure.json` and available diagnostics; they do not replace the last-success pointer. A failure does not mean the whole graph is unusable: read the first failed check and its evidence.

### Step 7 — CI and reruns

The **OULAD PostgreSQL integration** workflow starts PostgreSQL 16 on a GitHub runner, prepares Python 3.12/Java 21/Ontop, and executes the same 23-check fixture workflow, including SHACL and the committed-update experiment. Its `oulad-integration-evidence` artifact retains reports and logs for 14 days. It runs on push, pull request or a manual dispatch once committed/pushed. The full AAA data stays local. This new workflow has been prepared and the fixture has passed locally; its first remote run is still pending.

Keep `.env.integration` and `.runtime/` private/ignored. Commit the source, mapping, schema, fixture, requirements, workflow and documentation together; review selected generated evidence before committing it. No Git commit or push was performed for this extension. A green CI run does not itself configure branch protection.

If a connection fails, check Docker's health and port 5433. If Ontop reports an invalid file URI on Windows, the wrapper should be passing forward-slash relative paths. If the graph comparison fails, inspect `graph-comparison.json`; triple count alone is insufficient. If the source scope changed, rebuild the reference graph and intentionally revise the expected counts and queries. Stop the database without deleting its volume using:

```powershell
docker compose --env-file .env.integration -f docker-compose.postgres.yml stop
```

For the conceptual explanation, results and actual fixes, see [walkthrough section 16](docs/project-walkthrough.html#16-session-5-one-mapping-two-ways-to-answer). For sources, hashes and exact run identities, see [provenance section 12](docs/project-provenance.html#12-session-5-integration-provenance).

Course alignment: [Session 5 lab](../KRR/demos/session-05-integration/README.md). Technical references: [W3C R2RML](https://www.w3.org/TR/r2rml/), [Morph-KGC](https://morph-kgc.readthedocs.io/en/stable/documentation/), [Ontop CLI](https://ontop-vkg.org/guide/cli).

## 14. Session 6 — learning and baseline comparisons

This extension follows the Session 6 lab with **logistic regression**, **GraphSAGE node classification**, and **TransE link prediction**, always compared with simple count baselines. It reads the verified Session 5 RDF snapshot. It keeps labels, predictions and historical facts separate.

### Step 1 — activate the existing environment

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
python -c "import torch, torch_geometric, sklearn; import importlib.metadata as m; print('PyKEEN', m.version('pykeen'))"
```

The existing M2ENV already contains the needed learning libraries. No installation or environment replacement was required. Tested versions are recorded in `config/learning/tested-environment.json` and each run summary. CPU execution is supported; no GPU, Docker or live database service is needed. The code keeps PyKEEN/Matplotlib caches in ignored `.runtime/learning/`.

### Step 2 — check the source and protocol

Keep `data/interim/` and a successful Session 5 run in place. The runner selects the RDF identified by `outputs/integration/latest-full.json` and verifies its receipt and CSV fingerprints. If that pointer does not exist, it uses `data/processed/oulad.ttl`. A stale integration result is an error: rerun Session 5 or restore the corresponding inputs before training. For a fresh clone, first follow the download/selection/RDF instructions; the full learning experiment needs the AAA extract.

Read `config/learning/protocol.json` before running. The default asks about eventual Fail/Withdrawn outcomes at day 60, trains on 2013J and tests on 2014J with no shared students. The link experiment reconstructs hidden historical nonbanked submissions. It is not a future-submission forecast. The code and verification expect this documented AAA scope; changing the scientific question requires revising the protocol, checks and interpretation together.

### Step 3 — run the complete experiment

```powershell
.\run-learning.ps1
```

The helper runs `python src/learning/run.py`, then `python evaluation/verify_learning.py`. It stops on any failure. It creates a fresh run folder instead of overwriting earlier results. You can use those two commands separately if you want to distinguish training from saved-evidence verification.

The runner performs these stages in order:

1. Read the mapped RDF and independently reconcile labels/features with CSVs.
2. Build a separate label-free graph using only permitted day-60 observations. Save labels separately.
3. Exclude already-withdrawn enrollments and purge earlier records for students appearing in the future offering.
4. Fit imputation, constant-feature removal and scaling using training rows only.
5. Run training-prevalence and submission-count baselines, logistic regression and three GraphSAGE seeds.
6. Save the explicitly invalid label-leak control and random-split diagnostics separately from the headline temporal results.
7. Train three TransE splits and compare them with training popularity counts and random-rank references.
8. Produce figures, per-case predictions, metrics, checks, provenance and a readable HTML report.
9. Independently recheck metrics, partitions, preprocessing and all recorded file fingerprints.

### Step 4 — open and interpret the results

```powershell
Start-Process '.\outputs\learning\learning-results.html'
```

Read the [detailed Session 6 explanation](docs/learning-results-explained.html), also included in [walkthrough section 17](docs/project-walkthrough.html#17-session-6-learning-counts-and-an-honest-comparison). It includes initial counts, exact predictions, confusion matrices, all seeds, coefficient interpretation, errors/fixes and limitations.

The original data has 748 enrollments (531 successful, 217 unsuccessful). The temporal test has 340 eligible enrollments with **87 unsuccessful outcomes**; compare prediction counts with that test count. The documented run passes **21 learning checks and 54 saved-evidence checks**. Logistic regression leads the tested valid classifiers on average precision; popularity counts outperform TransE on all three link splits. The complex model is not automatically the better choice.

### Step 5 — find the evidence

```text
config/learning/protocol.json          Target, cutoff, years, seeds and fixed settings
src/learning/build_graph.py            RDF extraction and safe learning graph
src/learning/classification.py         Baselines, logistic regression and GraphSAGE
src/learning/link_prediction.py        TransE, count ranks and filtered evaluation
src/learning/checks.py                 Source reconciliation and leakage/cutoff tests
src/learning/report.py                 Charts and readable interpretation
src/learning/run.py                    Whole experiment with PROV-O and manifests
evaluation/verify_learning.py          Independently check saved evidence
outputs/learning/latest.json           Pointer to the latest successful run
outputs/learning/runs/<run-id>/
  graph/                              Features, separate labels, early edges and counts
  classification/                     Split lists, preprocessing, metrics and predictions
  links/seed-0/, seed-1/, seed-2/       Link partitions, models, ranks and metrics
  report.html                         Main results page
  summary.json                        Complete measured results and settings
  checks.json                         Learning checks
  verification.json                   Independent evidence checks
  manifest.json                       Input/output fingerprints
  provenance.ttl                      Actual learning activity and software
```

The scripts inside `src/learning/` implement stages used by `run.py`; run the complete runner rather than expecting every helper module to be a standalone command. Three PNG figures can be reused in a presentation. `.pt` model checkpoints and caches are ignored by Git; a clean clone needs a new training run before all saved-evidence checks can pass. A later source or code change can make an older run stale; keep its folder as historical evidence and create a new run with the current code.

### Step 6 — verify without retraining and understand limits

```powershell
python evaluation/verify_learning.py
# Or select an existing run explicitly:
python evaluation/verify_learning.py --run-dir outputs/learning/runs/YOUR_RUN_ID
```

Expect 54 passing evidence checks for this protocol. Inspect a failed assertion before retraining: a fingerprint mismatch means inputs or outputs changed, while a metric mismatch means the saved tables disagree. Failed training attempts keep their `failure.json` in the displayed run folder. CPU-only PyKEEN/Torch notices can appear without invalidating a completed run; use the final checks and exit status to judge completion.

This experiment does not automatically enter predictions into the original RDF, assign OWL outcome classes, update PostgreSQL, or make student decisions. The temporal test covers only one later offering. Scores are not established calibrated probabilities; link ranks measure reconstruction, not recommendation quality. Existing SHACL and integration CI remain separate; **the Session 6 training/evidence suite is currently local, not a new GitHub workflow**.


## 15. Session 7 — natural-language access

This stage turns English questions into SPARQL over the existing AAA RDF and RDFS. Read [the detailed explanation](docs/access-results-explained.html) for the pipeline, measured comparison, interpretation, fault tests and limitations. [Open the evaluated results](outputs/access/access-results.html).

### Step 1 — use the existing environment and check the local implementation

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
python evaluation/verify_access.py --local-only
# Equivalent local runner:
.\run-access.ps1
```

This generates `outputs/access/void.ttl`, `schema.txt`, `grounding.json`, `verification.json` and `local-results.html`. It executes the reference queries, reconciles them with CSV calculations, and tests guards, repair with scripted faults, scoring and the HTTP contract. It makes no model API calls. The original `data/interim/*.csv`, `data/processed/oulad.ttl` and `ontology/education.rdfs.ttl` must exist; on a fresh clone run the earlier preparation/RDF steps first. No new Conda environment, database service or package upgrade is needed in the tested M2ENV installation.

### Step 2 — inspect the schema, examples and prompt

```powershell
python src/access/grounding.py
python src/access/ask.py --list
python src/access/ask.py "How many distinct students are represented across AAA?" --show-prompt
```

Read `config/access/examples.ttl` (8 worked questions), `questions.yaml` (10 held-out answerable questions and 3 refusal questions) and `prompt.txt` (OULAD rules). The reference queries in the test file are used only for scoring; they are not retrieved as prompt examples. VoID reports actual observed data, including the difference between declared and populated classes.

### Step 3 — try a question with no API call

```powershell
python src/access/ask.py "How many enrollments are there in each offering?"
```

Default **catalog** mode runs an exact worked example: expect 2013J=383 and 2014J=365. It is a curated question interface, not a language model. Use `--list` to see the accepted wording. New wording needs live/record mode or an exact existing replay recording.

### Step 4 — ask Gemini using the lab key

```powershell
python src/access/ask.py "How many distinct students are represented across AAA?" --mode record --env-file 'D:\DESKTOP\M2\KRR\demos\.env'
```

Expected count: **712 distinct students**, not 748 enrollments. `record` calls Gemini and saves the genuine reply. `live` calls without caching. `replay` requires the exact model and prompt already recorded. The default model follows the lab: `gemini-3.5-flash-lite`. Use `--model MODEL_NAME` or `LLM_MODEL` to select another available Gemini model; availability and quota depend on your Google account. An explicit process environment value takes priority over loaded env files.

Alternatively copy `.env.access.example` to `.env.access` and set your own key there. `.env.access` is ignored by Git. Keep the real lab key in its current file; do not paste it into scripts or commit it. If the provider rejects the model/key or reaches quota, the command reports an error without automatically sending more requests. Inspect the saved incomplete run rather than counting the error as a refusal.

### Step 5 — reproduce the three-setting evaluation

```powershell
# Make fresh paid/free-tier API requests according to your account settings:
.\run-access.ps1 -Mode record -EnvFile 'D:\DESKTOP\M2\KRR\demos\.env' -MaxRequests 45

# Reuse the exact saved provider replies, making no API calls:
.\run-access.ps1 -Mode replay

# Audit current inputs, outputs and stored scores without calling Gemini:
python evaluation/verify_access.py
```

The evaluator compares **schema**, **examples** and **repair**. Each setting has the same 13 questions; normally 39 initial requests, with any repairs counted inside the 45-request limit. It prechecks all gold answers against the CSV oracle. Each run gets a new folder with `summary.json`, `answers.json`, `gold-answers.json`, `model-calls.json`, `report.html`, `manifest.json` and `provenance.ttl`. `latest-evaluation.json` advances only for a complete evaluation. F1 evaluates answer rows; refusals are counted separately. Read `completed` before interpreting a partial run. A replay is reproducibility evidence, not a new live model benchmark. Source changes can make saved evidence stale; the runner's initial local-only check permits generating a new evaluation, followed by a complete audit.

### Step 6 — open the question interface

```powershell
# No-key catalog mode:
python src/access/serve.py

# Or new natural-language questions with Gemini:
python src/access/serve.py --mode record --env-file 'D:\DESKTOP\M2\KRR\demos\.env'
```

Open **[http://127.0.0.1:8007](http://127.0.0.1:8007)**. Choose an example, click Ask, and inspect the answer, generated SPARQL and attempts. Keep the terminal open; **Ctrl+C** stops the server. If port 8007 is occupied, use `--port 8008` and open that address. The server binds only to your computer and has a default lifetime limit of 45 model requests. Catalog mode consumes none. The server's replay mode supports only questions/settings previously recorded exactly; ordinary catalog examples may not be in a cache containing only the held-out evaluation.

The lab-style TEXT2SPARQL contract is also available:

```powershell
$question = [uri]::EscapeDataString('How many enrollments are there in each offering?')
Invoke-RestMethod "http://127.0.0.1:8007/?question=$question&dataset=https%3A%2F%2Fexample.org%2Foulad%2F"
Invoke-RestMethod 'http://127.0.0.1:8007/health'
```

JSON includes `dataset`, `question`, `query`, `status`, `result` and `attempts`. Missing-data refusals have an empty SELECT for contract compatibility, plus an explicit refusal status/reason. That empty query is not evidence that a missing fact has the value zero. Provider failures return HTTP 503. A wrong dataset or empty question returns 400.

Port **8007** is this English-question interface; **3030** is Fuseki, **7474** is Neo4j Browser, **7687** is Neo4j Bolt, and the project PostgreSQL host port remains **5433**. The Session 7 implementation executes the local graph, so starting those services is optional for this stage. It does not add predicted outcomes to the historical RDF.

### Interface refresh — 19 October 2026

The explorer now has a responsive sidebar, dataset counters, an eight-question library, clearer loading/error states and separate **Answer**, **SPARQL** and **Checks** tabs. You can copy the generated query, export returned rows as CSV, use Ctrl+Enter to submit, and open the dataset explanation. The counters come from the loaded graph; the display does not add invented results. The UI files are in `src/access/ui/` and are included in run fingerprints. No fonts, scripts or images are downloaded from external services.

The reviewed preview is available at **http://127.0.0.1:8008/** in no-API catalog mode. Port 8008 was used because the original port-8007 preview kept returning the earlier page during testing. The normal command still defaults to 8007; run `python src/access/serve.py --port 8008` to reproduce the reviewed preview. An older preview process must be restarted to load a changed Python page renderer.

The refresh passed browser checks at 1440, 768 and 390 pixels, including choosing examples, returned counts, all result tabs, the explanation dialog, unsupported-question recovery and CSV export. The complete cached evaluation was replayed with zero API requests, followed by 65 passing local/evidence checks. Historical live responses were retained; the UI refresh is not a new live model benchmark.

For the remaining final-submission requirements, read [the course coverage audit](docs/course-coverage-audit.html). The interface redesign does not replace entity-resolution evaluation, whole-stack deployment or the final report/open-problem work.

### Two questions to test the live page

Use **Gemini · live** or **Gemini · recorded**, rather than the catalog, for these exact questions:

| Copy this question | Expected behavior | Interpretation |
|---|---|---|
| How many distinct students are in the dataset? | An answer of **712**, with SPARQL and checks. | Students are distinct people; 748 is the number of enrollments. |
| What personal reasons caused students to withdraw from AAA? | **Refused**, with an explanation that personal reasons are not recorded. | Withdrawal outcomes exist, but their causes are unavailable. |

Inspect **Answer**, **SPARQL** and **Checks**. An empty result is not automatically a refusal. A refusal has `status=refused` and a reason; an exhausted repair has `status=invalid`; provider/key/quota failures are service errors. Gemini is not guaranteed to interpret every new wording correctly. The current small benchmark is separate from this interactive demonstration.

For a direct Conda launch, run:

```powershell
conda activate M2ENV
cd D:\DESKTOP\M2\kr-oulad
python src/access/serve.py --mode live --port 8009 --env-file 'D:\DESKTOP\M2\KRR\demos\.env' --model gemini-3.5-flash-lite --max-requests 10
```

Open http://127.0.0.1:8009/. Direct `serve.py` is a low-level command; use the launchers below for mandatory startup SHACL validation. The page displays a result once processing completes, rather than streaming tokens. Opening the page makes no model request. Each submitted question can use up to three requests with repairs; the ten-request cap applies to one server process and resets when it restarts.

### Step 7 — inspect and commit the evidence

Open `outputs/access/access-results.html`, `docs/access-results-explained.html` and the updated provenance/walkthrough. Inspect `git status`; include the access scripts, configuration, examples, tests, run evidence and documentation. The stored benchmark cache contains genuine model replies and no API key. No commit or push is performed by the runner. This stage currently has local verification, not a new GitHub workflow; the earlier SHACL/integration workflows remain separate.

## 16. One launcher for the full project

Use the existing **M2ENV**, Java on PATH, and Docker Desktop with its Linux engine running. The launcher checks these prerequisites without installing packages or creating an environment. It locates the sibling `KRR/demos` folder by default. Existing raw files are verified and reused; missing data may require a download.

```powershell
conda activate M2ENV
cd D:\DESKTOP\M2\kr-oulad
.\run-project.ps1
```

This performs the following stages, stopping on the first unexpected failure:

1. Download/verify data, profile raw tables, select AAA, profile the subset, build RDF, validate it and check competency questions.
2. Prepare the OWL ontology, reason over the sample and full graph, verify semantics, and execute/export the ontology notebook.
3. Run SHACL examples, expected failure cases and verification.
4. Start the project PostgreSQL service and run mappings, materialization, virtualization and their verification.
5. Train the Session 6 models and verify their saved evidence.
6. Start the existing lab Neo4j/Fuseki services and load/verify the OULAD views.
7. Run a final SHACL gate, regenerate the VoID/schema description, run local access checks, then open the live Gemini page.

The default page port is **8009**. If occupied, the Conda launcher tries the next ten ports and opens the actual selected URL. It never stops another server to obtain a port. Keep the terminal open; **Ctrl+C** stops the newly launched page. Database containers remain running.

For everyday use with already prepared RDF:

```powershell
.\run-project.ps1 -AccessOnly
```

This still runs the SHACL gate, updates the schema description and checks access locally. It does not redo preparation, ontology, databases or training and does not need Docker/Java. Validation can take around a minute or longer; the browser opens after it passes.

Useful options:

```powershell
# Check prerequisites and show the plan, without running it:
.\run-project.ps1 -CheckOnly

# Use an explicitly located lab key file:
.\run-project.ps1 -AccessOnly -EnvFile 'D:\DESKTOP\M2\KRR\demos\.env'

# Open the no-API catalog after validation:
.\run-project.ps1 -AccessOnly -Mode catalog

# Full pipeline without the optional Neo4j/Fuseki views (PostgreSQL still runs):
.\run-project.ps1 -SkipGraphServices

# Run the full pipeline and exit, useful for verification:
.\run-project.ps1 -NoServe -NoBrowser
```

Other options are `-Port`, `-Model`, `-MaxRequests` (default 10), `-LabCompose`, and `-NoBrowser`. Credential lookup is: explicit `-EnvFile`, otherwise project `.env.access`, otherwise sibling `KRR/demos/.env`; existing process environment values take precedence. Credentials are not copied into the repository.

The launcher writes an execution receipt under `outputs/project/runs/<id>/summary.json` and a successful-pipeline pointer in `outputs/project/latest.json`. It records completed/failed stages, interpreter, launcher hash and validated input hashes. Each stage keeps its own reports and PROV records. Full reruns refresh generated outputs and replace the six managed PostgreSQL tables; earlier retained integration/learning run folders remain. No commit or push occurs. The launcher runs local access checks, **not a fresh paid Gemini benchmark**; use Session 7's separate evaluation command when needed.

## 17. Docker container for the live Gemini page

This container serves the existing RDF graph and the access interface. Data preparation, OWL reasoning, model training, PostgreSQL, Neo4j and Fuseki remain in their existing workflows. **M2ENV does not need to be activated for this Docker option.** Gemini still runs through Google's API, so internet access and a valid key are needed for submitted questions.

Open Docker Desktop, wait for its Linux engine, then run:

```powershell
cd D:\DESKTOP\M2\kr-oulad
.\start-access-docker.ps1
```

The helper builds the image, starts the container, waits for SHACL validation and a healthy page, and opens **http://127.0.0.1:8010/**. The first image build needs internet access and can take several minutes. Later builds reuse Docker's cache. The badge should read **Gemini · live**. Port 8010 is separate from the earlier Conda page on 8009 and catalog on 8008. If 8010 is occupied by another application, use `-Port 8011`.

Use the **712-student question** and the **personal-reasons refusal** from section 15. The container starts with a cap of ten Gemini requests, up to three per question including repairs. Opening/checking the page makes no request. A manual container restart resets the cap.

```powershell
# Explicit key location, another port, and a request cap:
.\start-access-docker.ps1 -EnvFile 'D:\DESKTOP\M2\KRR\demos\.env' -Port 8010 -MaxRequests 10

# Keep genuine interactive responses for later inspection:
.\start-access-docker.ps1 -Mode record

# Inspect service status and startup/validation output:
docker compose -f docker-compose.access.yml ps
docker compose -f docker-compose.access.yml logs --tail 60 access

# Stop this container; retain host reports and project data:
.\start-access-docker.ps1 -Stop
```

The equivalent Compose command with the default sibling lab key location is:

```powershell
docker compose -f docker-compose.access.yml up --build -d --wait --wait-timeout 300
Start-Process 'http://127.0.0.1:8010/'
```

For a different key file, the helper's `-EnvFile` is easiest. Direct Compose accepts `OULAD_GEMINI_ENV_FILE`, `OULAD_ACCESS_PORT`, `OULAD_ACCESS_MODE`, `OULAD_ACCESS_MODEL` and `OULAD_ACCESS_MAX_REQUESTS`. The helper restores prior environment settings after it runs. It prefers `.env.access` when present, otherwise the sibling lab `.env`. Do not put a real key in the Dockerfile or Compose file.

### What Docker validates and saves

- The RDF, RDFS and SHACL files are mounted read-only, then copied into a container-local snapshot. Queries keep using this validated snapshot until the container restarts. Rebuild/restart after changing host inputs or code.
- The normal SHACL policy applies: violations or missing required targets block startup; warnings remain visible and do not block it. The known snapshot has 0 violations and 5 warnings.
- The HTTP server binds inside the container, while Docker publishes only on your computer's `127.0.0.1`. The image runs as a non-root user.
- The API-key file is supplied as a [Docker Compose secret](https://docs.docker.com/compose/how-tos/use-secrets/). The entrypoint reads only the Google key from it. The build context excludes datasets, outputs, Git history and environment files; credentials are not baked into the image.
- Startup receipts and SHACL report/PROV files appear under `outputs/docker-access/container/runs/<id>/`; `outputs/docker-access/container/latest.json` identifies the last validated startup. The actual HTTP readiness is reported by Docker's health check.
- The schema/VoID export is under `outputs/docker-access/access/`. In record mode, `access/llm-cache.json` retains genuine replies. Live mode does not persist question/answer histories. Startup receipts count zero requests at startup; they are not a continuously updated usage log or a new benchmark.

The agent still constructs its prompt description with `grounding.describe()`; it exports `void.ttl` but does not parse that export as its prompt input. Query checks establish executable, allowed SPARQL; they do not prove that every generated query correctly interprets a question.

If startup fails, read the container logs and SHACL report. Do not bypass a failed gate. A missing RDF file requires running the preparation pipeline first. Key/quota/provider errors occur when submitting questions and are separate from SHACL validation. The container does not auto-restart repeatedly on failures.

## Sources and reuse

- Official dictionary: https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/
- UCI download/license: https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset
- Dataset citation: Kuzilek, Hlosta, Zdrahal (2017), https://doi.org/10.1038/sdata.2017.171 (CC BY 4.0)
- RDFS semantics: https://www.w3.org/TR/rdf-schema/
- Local course patterns: Session 1 profiling.py; Session 2 RDFLib conversion, SPARQL, and rdfs_entailment_demo.py.

Tested environment: Python 3.12.15, pandas 2.3.3, RDFLib 7.6.0, owlrl 7.6.2,
ydata-profiling 4.18.4, pySHACL 0.40.1. The original stages used these versions. Session 5 additionally installed Morph-KGC 2.10.0 without changing the existing dependency versions; see section 13.

Raw data are gitignored; generated evidence is organized under outputs/. Commit scripts, schema,
queries, docs, and selected final evidence. Keep secrets out of commits.

