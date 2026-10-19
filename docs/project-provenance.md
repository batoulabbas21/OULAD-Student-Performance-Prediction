# OULAD project provenance

**Where the data came from, what we changed, and why the results can be traced.**

Prepared on **13 October 2026**, updated through Session 7 on **18 October 2026** for the `kr-oulad` project. This guide describes the current AAA build and links to its evidence. Start here for the project's origins; use the [README](../README.md) for commands. Jump to [SHACL evidence](#session-4-validation-evidence), [SHACL and CI](#shacl-and-ci-what-is-implemented-and-what-has-run), or [validation-run provenance](#10-connection-to-the-course-provenance-lesson).

> **Provenance means the history behind a result.** For this project, it connects an original CSV row to its RDF representation, the ontology definition applied to it, and the resulting answer.

## 1. The project in one minute

The project turns a small, understandable part of OULAD into a knowledge graph. It keeps student identity separate from enrollment in a particular offering, answers questions with SPARQL, uses OWL reasoning to classify records, and applies SHACL rules to validate the supplied graph.

| Current scope | Recorded result |
|---|---|
| Selected module | AAA, across offerings 2013J and 2014J |
| People and participation | 712 distinct student IDs; 748 enrollments |
| Assessment data | 12 assessments; 3,149 assessment records |
| Learning resources | 413 resource descriptions |
| Asserted RDF | 28,470 data triples, with a separate 105-triple RDFS schema |
| OWL results | 6,119 additional named type assertions |
| Saved verification | 14 core checks, 17 ontology checks and 37 SHACL checks passed |
| SHACL gate | 0 violations, 5 visible warnings; gate passes |
| SHACL CI | User screenshot: Success at `afd8535` on main; 31 fixture regression checks configured |
| Session 5 | 28,470 mapped triples; 23 integration checks passed for full AAA and 23 for the fixture |
| Integration CI | New PostgreSQL fixture workflow prepared; no remote run evidence recorded here |
| Session 6 learning | 21 learning checks and 54 evidence checks passed; predictions retained separately |
| Session 7 access | 65 local/evidence checks passed; measured Gemini comparison recorded |

The current build excludes daily activity from `studentVle.csv`. An activity question is therefore marked **unavailable**; omitted activity does not mean that students made zero clicks.

## 2. Original sources and credit

### Dataset: OULAD

The source is the **Open University Learning Analytics Dataset**, by **Jakub Kuzilek, Martin Hlosta and Zdenek Zdrahal**, distributed through the [UCI dataset page](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Dataset citation: Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2015). *Open University Learning Analytics dataset* [Dataset]. UCI Machine Learning Repository. [Dataset DOI: 10.24432/C5KK69](https://doi.org/10.24432/C5KK69).

The project's download manifest also cites their 2017 dataset paper, *Scientific Data*, 4, 170171: [article DOI: 10.1038/sdata.2017.171](https://doi.org/10.1038/sdata.2017.171). The dataset DOI and article DOI identify different publications.

The [download manifest](../data/raw/manifest.json) records the source archive URL, file sizes and SHA-256 fingerprints. The originals remain in `data/raw/`; the selected and transformed data are stored separately.

### Vocabulary: a selected FOAF fragment

The ontology reuses `foaf:Person` and `foaf:Agent` from the [FOAF Vocabulary Specification 0.99](https://xmlns.com/foaf/spec/), by **Dan Brickley and Libby Miller**, copyright 2000–2014. Its accompanying RDF is licensed under [CC BY 1.0](https://creativecommons.org/licenses/by/1.0/).

The complete downloaded RDF is retained in [ontology/imports/foaf.rdf](../ontology/imports/foaf.rdf). The preparation step extracts the two class declarations, their labels and comments, and the source relationship `foaf:Person rdfs:subClassOf foaf:Agent`, with a project header. The project adds `edu:Person rdfs:subClassOf foaf:Person`.

Reasoning uses this **documented fragment**, not the full FOAF vocabulary. See the [reuse and attribution notes](../ontology/imports/README.md) for the selection and its limits.

### Course methods and project development

The workflow adapts the local KRR labs: Session 1 for profiling, Session 2 for RDF/RDFS, SPARQL and graph access, Session 3 for ontology imports and reasoning, and Session 4 for SHACL validation, triage and a severity-based gate. Session 3 references include [local_reasoner.py](../../KRR/demos/session-03-ontology/local_reasoner.py), [check_my_axioms.py](../../KRR/demos/session-03-ontology/check_my_axioms.py), and [realize_sample.py](../../KRR/demos/session-03-ontology/realize_sample.py).

The OULAD model, scripts and explanations were developed for this project with Codex assistance. The education classes and rules are project modeling choices; the source dataset does not supply this ontology. A project-wide code license has not been established. The dataset and FOAF licenses apply to their respective material.

## 3. The journey from CSVs to answers

**Download → select AAA → profile → create RDF → validate with SHACL → query and reason → inspect and verify.**

| Stage | What happens | Main evidence |
|---|---|---|
| Download | `fetch_data.py` retrieves the seven original CSV tables and records their fingerprints. | [Raw manifest](../data/raw/manifest.json) |
| Select | `select_subset.py` keeps AAA's two offerings and their related rows. Assessment records are selected through assessment IDs. | [Selection settings and counts](../data/interim/selection.json) |
| Profile | `profiling.py` reports distributions, missing values, keys and relationships for the selected scope. | [Subset profile](../outputs/profiling/subset/profile.html) |
| Convert | `convert_to_rdf.py` maps selected rows to stable identifiers, links and typed values using the authored RDFS vocabulary. | [RDF facts](../data/processed/oulad.ttl) and [graph summary](../data/processed/graph_summary.json) |
| Validate | `src/validation/validate.py` checks asserted facts using shapes and the RDFS class hierarchy. It writes a report and actual-run provenance. | [SHACL report](../outputs/shacl/full/report.html) and [PROV-O record](../outputs/shacl/full/provenance.ttl) |
| Query | `run_queries.py` executes the competency questions and records answer availability. | [Answer status](../outputs/answers/status.json) |
| Prepare OWL | `prepare_ontology.py` prepares the RDFS-based OWL declarations, local imports, FOAF fragment and a small example dataset. | [Preparation record](../outputs/ontology/preparation.json) |
| Reason | `owl_reasoner.py --full-data` uses HermiT through Owlready2 to check consistency and classify the full graph. | [Reasoner report](../outputs/ontology/reasoned-full.json) and [inferred types](../outputs/ontology/inferred-types-full.ttl) |
| Verify and explain | Verification compares results with source-derived expectations; the notebook displays saved results. | [Core checks](../outputs/verification.json), [ontology checks](../outputs/ontology/verification.json), [results notebook as HTML](../outputs/ontology/ontology-results.html) |

The preparation and conversion entry scripts share logic in [src/common/pipeline.py](../src/common/pipeline.py). Their folder names follow this project's structure while preserving the lab workflow.

### Which table contributes what?

| Original table | Contribution to this build |
|---|---|
| `courses.csv` | Module offerings and their lengths |
| `studentInfo.csv` | Student IDs, contextual enrollment attributes and recorded final outcomes |
| `studentRegistration.csv` | Registration and withdrawal day offsets linked to enrollments |
| `assessments.csv` | Assessment type, weight, offering and known deadline |
| `studentAssessment.csv` | Assessment record, recorded score, submission day and banked flag |
| `vle.csv` | Learning resource descriptions linked to offerings |
| `studentVle.csv` | Downloaded and retained; excluded from this core build |

## 4. Choices that affect the meaning

These decisions explain how the source becomes a graph. Full notes are in [modeling decisions](decisions.md) and [questions and rules](questions-and-rules.md).

- **One person can have several enrollments.** Student IDs identify people; the module, offering and student ID together identify an enrollment. Final outcome belongs to that enrollment.
- **Unknown values stay unknown.** The reader interprets `?` as missing. Optional missing values produce absent RDF properties. Three unknown scores and two unknown deadlines remain unresolved.
- **Days remain offsets.** Negative values can refer to days before the offering starts. The project does not fabricate calendar dates.
- **An assessment record may be banked.** A transferred result is not necessarily a new submission. This motivates the name `AssessmentRecord`.
- **“Late” is an operational query definition.** A record must be explicitly nonbanked, have both recorded dates, and have submission day greater than deadline day. This does not establish misconduct or account for individual extensions.
- **“Low score” means a known score below 40.** It does not establish failure of the whole module. “Successful enrollment” means a recorded outcome of Pass or Distinction.
- **Ontology axioms and data checks have different jobs.** RDFS domains/ranges infer types. OWL uses open-world reasoning: a missing link alone is not a required-field violation. Python checks assess the supplied tables; Session 4 SHACL checks the explicit graph requirements after conversion. Warnings remain visible, while violations and empty required targets block the project gate.

The identifiers beginning `https://example.org/oulad/` are project identifiers. Their spelling does not imply that an online service publishes those resources.

## 5. A real result, traced all the way back

**Question: Why is enrollment `AAA / 2013J / 100893` classified as successful?**

1. **Original evidence.** In [raw studentInfo.csv](../data/raw/studentInfo.csv), the row with `code_module=AAA`, `code_presentation=2013J` and `id_student=100893` has `final_result=Pass`. It is physical line 26, including the header, in this audited file.
2. **Selection.** The same key and outcome appear in [selected studentInfo.csv](../data/interim/studentInfo.csv). This row is retained because it belongs to AAA.
3. **Representation.** The converter creates the enrollment identifier and records its type and outcome in [oulad.ttl](../data/processed/oulad.ttl):

```turtle
@prefix edu: <https://example.org/oulad/schema#> .

<https://example.org/oulad/id/enrollment/AAA/2013J/100893>
    a edu:Enrollment ;
    edu:finalResult "Pass" .
```

4. **Authored definition.** [education.owl.ttl](../ontology/education.owl.ttl) defines `SuccessfulEnrollment` as equivalent to an enrollment with outcome Pass or Distinction. This definition is the project's interpretation of success.
5. **Derived conclusion.** The saved HermiT result adds the following assertion to [inferred-types-full.ttl](../outputs/ontology/inferred-types-full.ttl):

```turtle
@prefix edu: <https://example.org/oulad/schema#> .

<https://example.org/oulad/id/enrollment/AAA/2013J/100893>
    a edu:SuccessfulEnrollment .
```

The successful type is absent from the asserted RDF and present in the inferred file. This is a classification of a recorded outcome, not a prediction of future performance. The [provenance snapshot](provenance-snapshot.json) records this trace and the source fingerprints checked for it.

## 6. Four kinds of information to keep separate

| Kind | Example | Where it originates |
|---|---|---|
| Source fact | An enrollment has recorded outcome Pass. | An OULAD CSV row |
| Project definition | Pass or Distinction qualifies as a successful enrollment. | The authored OWL ontology |
| Inferred fact | That enrollment is a `SuccessfulEnrollment`. | Source facts plus the definition, processed by HermiT |
| Teaching example | A fictional individual makes an intentionally faulty ontology inconsistent. | Isolated files in `ontology/exercises/` and the generated ontology workspace |

The small ontology sample selects seven real enrollments and their related facts. Synthetic error demonstrations use the separate `https://example.org/oulad/teaching#` namespace. They are not evidence about OULAD students and are not loaded as real data into the project databases.

## 7. What the saved checks establish

The core verification records **14 passed checks**, including source-versus-graph counts, outcome answers, late-record identities and preservation of unknown scores. The ontology verification records **17 passed checks**, including consistency, inferred identities, sample fidelity and controlled examples of OWL semantics.

| Inferred class | Expected from CSVs | Inferred by OWL |
|---|---:|---:|
| SuccessfulEnrollment | 531 | 531 |
| WithdrawnEnrollment | 126 | 126 |
| LowScoreAssessmentRecord | 90 | 90 |
| BankedAssessmentRecord | 42 | 42 |
| NonBankedAssessmentRecord | 3,107 | 3,107 |
| EnrollmentWithLowScore | 75 | 75 |

Evidence: [class counts](../outputs/ontology/inferred-class-counts.csv) and [identity comparisons](../outputs/ontology/verification.json). The clean ontology and loaded data are consistent, with no unsatisfiable named classes in the saved run. That finding concerns the supplied axioms and data; it does not prove that the data describe the world perfectly.

The exported 6,119 assertions are **additional named class memberships**, not the complete set of all possible OWL conclusions. The notebook's seven saved code cells have executed outputs and no error outputs.

### Session 4 validation evidence

The full asserted AAA graph has **0 violations and 5 warnings**. The warnings identify the three unknown scores and two unknown exam deadlines; their exact focus nodes match the selected CSV rows. Strict SHACL conformance is false because warnings are present, while the project's documented gate policy passes.

All 14 target-bearing shapes have coverage counts. Thirteen are populated; the optional DailyInteraction target is empty because activity was not loaded. Seven structural target counts were independently checked against CSV-derived counts.

The verification report records **37 passed checks**, including bad links, score boundaries, incorrect datatypes, duplicate keys, cross-offering relationships, date semantics and the empty-target trap. The real sample passes with 3 warnings; its one-link broken variant fails with 1 violation and the same 3 warnings. The naive draft flags those three missing values as violations, showing why triage changes the policy without changing the facts.

Read the [rule coverage and triage decisions](shacl-triage.md), [full results](../outputs/shacl/full/report.html) and [SHACL verification](../outputs/shacl/verification.json). The following section distinguishes those saved local results from the prepared CI workflow.

### SHACL and CI: what is implemented and what has run

**Yes: SHACL verification includes a CI workflow.** CI means continuous integration: a remote runner automatically checks relevant code changes. SHACL defines the validation rules; CI decides when to execute the validator and tests. Running the scripts on your computer is local verification, not a GitHub Actions run.

| Execution path | Data and checks | Evidence/status |
|---|---|---|
| Full local validation | All 28,470 asserted AAA triples; 0 violations and 5 warnings. | [Saved full report](../outputs/shacl/full/report.html); gate passes. |
| Full local verification | 37 checks: 31 shared sample/fault checks plus 6 full-data evidence checks. | [Saved verification](../outputs/shacl/verification.json); all passed on 15 October 2026. |
| GitHub Actions CI | Real sample validation, 31 shared checks using `--sample-only`, then a separate check that the broken fixture exits with code 1. | User-provided GitHub screenshot shows **Success** at commit `afd8535`, branch `main`, duration 34s (validate job 29s). No run URL or independent API check is recorded. |

The CI check count is **31, not 37**. The six additional local checks compare the full run's inputs and validator, confirm sample triples belong to the source graph, compare seven entity counts with CSVs, match warning identities to missing CSV values, check the full gate result, and verify the full run's PROV-O input/output fingerprints. Those six require the full local extract and saved report, so sample-only mode skips them. The 31 shared checks passed locally. Remote SHACL success is separately supported by the screenshot supplied by the user.

The workflow is named **OULAD SHACL gate**, with job ID `validate`. It listens for relevant pushes and pull requests, and also defines a manual `workflow_dispatch` trigger. Its path filters cover shapes, the RDFS schema, validation code, SHACL fixtures, the verifier and the workflow itself. A README-only change therefore does not trigger this workflow automatically.

The runner uses Ubuntu, Python 3.12, pySHACL 0.40.1 and RDFLib 7.6.0. Installation occurs on the runner; your existing local **M2ENV** is unchanged. It needs neither Docker, Neo4j, Fuseki nor the raw OULAD download. The fixture files are outside the ignored `data/` directory so they can be included in Git.

**How CI decides whether to pass:** the real sample must pass its gate; the verifier must pass all 31 checks; the deliberately broken sample must return **exit 1**. That expected failure makes the final test pass, because it proves the gate rejects the known bad link. An unexpected exit 0 or an execution error (exit 2) makes that step fail. The two fixture checks are separate workflow steps, not extra numbered regression checks.

**Remote evidence:** the user committed and pushed the SHACL work, then supplied the successful-run screenshot. The screenshot is the evidence for the recorded conclusion; the full commit SHA and run URL were not supplied. No GitHub API query or branch-protection change was performed for this update. The new integration workflow still needs its own first push/run.

**Merge enforcement is separate.** To require a passing check before merging, configure the repository's branch protection or ruleset. Before making this particular workflow required for every pull request, adjust its workflow-level path filters: a skipped workflow can leave a required check pending on unrelated changes. GitHub documents this behavior in [troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks). No merge protection was changed by this task.

The current workflow does not upload downloadable report artifacts or capture a GitHub run URL in the project provenance. The successful SHACL screenshot is identified separately from local run records. The new integration workflow is configured to upload its own reports when it runs.

## 8. How Neo4j, Fuseki and the notebook relate

All three views ultimately use the project data; they do not introduce another original dataset.

| View | What the saved evidence describes | Meaning of its results |
|---|---|---|
| Neo4j | 5,037 project nodes and 8,221 relationships in snapshot `c87470abc5b822ca`; 815 late records matched. [Import report](../outputs/neo4j/import-summary.json). | A property-graph projection, with selected superclass labels. It is not a full OWL reasoning service. |
| Fuseki | 28,575 triples: 28,470 facts plus 105 RDFS triples. Six available queries passed. [Verification report](../outputs/fuseki/import-summary.json). | SPARQL over the stored graph. Automatic RDFS inference is disabled in this configuration. |
| Ontology notebook | Saved reasoner results, graph queries, inferred class counts and explanations. [Open the report](../outputs/ontology/ontology-results.html). | Shows the OWL results, including comparisons between asserted and inferred types. |

The OWL type export is separate; it is not automatically loaded into Neo4j or Fuseki. These import reports document saved checks. This provenance audit did not contact either server or establish whether it is currently running.

## 9. Dates, fingerprints and reproducibility

| Recorded event | UTC time | Interpretation |
|---|---|---|
| Raw manifest | 10 October 2026, 19:30:38 | Retrieval **or re-verification**, as named in the manifest; not the original research collection date |
| Fuseki verification | 12 October 2026, 06:38:19 | Check of the already loaded graph |
| Ontology preparation | 13 October 2026, 08:00:00 | Generated local imports and sample |
| Full reasoner report | 13 October 2026, 09:58:55 | Saved classification report timestamp |
| Ontology verification | 13 October 2026, 10:01:38 | Saved test report timestamp |
| Initial provenance audit | 13 October 2026, 13:05:14 | Original file-level inspection |
| Latest saved full SHACL validation | 15 October 2026, 02:51:37 | Existing Session 4 report at the current project location |
| Latest saved SHACL verification | 15 October 2026, 02:51:53 | 37 checks passed; fingerprints match that report |
| First Session 4 provenance audit | 14 October 2026, 06:39:15 | Preserved in the historical snapshot |
| Full Session 5 integration | 16 October 2026, 10:33:10 | 23 checks passed; separate mapped-graph SHACL report |
| Session 5 provenance audit | 16 October 2026, 10:36:10 | Refreshed saved-stage fingerprints and recorded new full/fixture integration evidence |

The audit checked **all seven raw CSVs** against the manifest. It also checked the four input fingerprints stored by the full reasoner report, and the two stored by the Fuseki report. All matched the current files. All four saved SHACL runs (full, sample, broken and draft) have matching input and validator fingerprints at the new location. Their PROV-O records match the three input entities, software agent and five generated report-file fingerprints. The latest verification fingerprint matches the latest full summary.

The accompanying [provenance-snapshot.json](provenance-snapshot.json) records full SHA-256 fingerprints for the selected data, code, ontology, shapes, fixture, workflow, documentation and result files listed in its `files` object. A fingerprint helps detect file changes; these local fingerprints are not publisher-authenticated signatures. They capture the files inspected now, not an independently archived history of every earlier run.

The [previous snapshot](history/provenance-snapshot-2026-10-15T024327Z.json) preserves the 15 October audit; the earlier 14 October snapshot also remains in history. The current Session 4 full run is `7b97ef4623a9455c8781799ac0fb1471`. The new Session 5 mapped-graph validation has its own run ID, recorded below.

**Folder relocation:** the project is now `D:\DESKTOP\M2\kr-oulad`, with the course in `D:\DESKTOP\M2\KRR`. Earlier reports retain their original `C:` input paths. We compared those inputs by role and SHA-256 with files at the new location, preserving the original reports. To create fresh reports with current paths, activate M2ENV, enter the project folder and run `./run-shacl.ps1`. Running only the full verifier against old absolute paths can fail; run the full helper first.

The current environment is the existing Conda **M2ENV**: Python 3.12.15, pandas 2.3.3, RDFLib 7.6.0, owlrl 7.6.2, Owlready2 0.51 and pySHACL 0.40.1. The snapshot includes additional notebook and profiling package versions. This inventory describes the environment inspected now. The [README](../README.md) contains the execution order, Java requirement, ontology steps and optional database instructions.

After changing data, mappings or axioms, regenerate their dependent outputs and verification reports before updating this guide. Reordered Turtle serialization can change a file's fingerprint even when its RDF meaning is unchanged.

## 10. Connection to the course provenance lesson

The [W3C PROV-O model](https://www.w3.org/TR/prov-o/) describes provenance using entities, activities and agents. Here is how those ideas fit this project:

| PROV idea | Plain meaning | Project example |
|---|---|---|
| Entity | An input or output | A CSV, the RDF graph, an ontology file or an answer table |
| Activity | Work that uses or produces entities | Subsetting, conversion, querying or reasoning |
| Agent | A person, organization or program responsible for work | Dataset authors, the project modeler or the conversion program |
| Derivation | An output depends on an input | The inferred types depend on the asserted RDF and ontology |

This guide and its snapshot provide **documented file-level provenance**, plus a checked row-to-inference example. Since Session 4, validation emits a machine-queryable PROV-O record for each actual run. Session 5 also records a complete integration activity, its database state, mapping and outputs. It does not annotate every source triple or reconstruct all earlier pipeline executions.

The course's [Session 4 add_provenance.py](../../KRR/demos/session-04-shacl/add_provenance.py) motivates the new [validation provenance record](../outputs/shacl/full/provenance.ttl). It describes the validation that actually ran:

- **Entities:** the data, RDFS schema and SHACL shapes, identified by SHA-256; the generated report files also have fingerprints.
- **Activity:** a unique validation run with recorded start and end times. The PROV activity includes report assembly; `summary.json` separately records the validation finish time.
- **Software agent:** the project validator identified by its code fingerprint, with its pySHACL version.
- **Links:** `prov:used` connects the run to its inputs; `prov:wasGeneratedBy` connects reports to the run; `prov:wasAssociatedWith` identifies the software.

Run `python src/validation/show_provenance.py` to answer which inputs and software produced the full report. Each output folder holds the latest run; its files are replaced on rerun. This is validation-run provenance, not a claim of immutable history for the entire project.

## 11. What this record cannot establish

The selected AAA offerings are a teaching scope. Results do not describe all university students, reveal the real module title, or establish causal explanations of performance. Missing activity and unknown values remain limits on the questions that can be answered.

The project has not recorded a complete immutable history of each past code version, execution start/end times for every earlier stage, or provenance for every triple. SHACL runs now record their own times and input/output identities. Some stages have only saved reports and current source files. This guide states those limits so its evidence can be used at the level actually supported.

**To explain the project aloud:** “We obtained OULAD from UCI, preserved the originals, selected AAA and checked its tables. We mapped the selected records into RDF, authored an education ontology with a small attributed FOAF fragment, and used HermiT to derive classifications. We validated the asserted graph with SHACL, triaged unknown values as warnings, and checked that deliberate faults fail the gate. We compared the graph answers and inferred identities with the CSVs. The manifests, source files and verification reports let us trace those results back to their inputs.”


## 12. Session 5 integration provenance

**What changed:** the existing selected AAA CSVs were loaded into PostgreSQL; a shared R2RML mapping was executed by Morph-KGC and queried by Ontop. The original raw CSVs, reference RDF, RDFS/OWL vocabulary and SHACL shapes remain the source of comparison. This adds a relational access path and a reusable declarative mapping, not a new original dataset.

The design adapts the course's [Session 5 lab](../../KRR/demos/session-05-integration/README.md): database loading, mapping materialization, comparison with Session 2, Ontop querying and SQL inspection. OULAD's composite enrollment identity, joins and missing-value rules replace the lab's supply-chain model. Entity-resolution exercises are outside this extension: the supplied OULAD IDs already determine the modeled joins.

| Evidence | Full AAA | Real-data fixture |
|---|---|---|
| Integration run | `99568e1cd42b46aa8ddf05ac6d075a5b` | `75d6a50e89424e6fa9872844093196e9` |
| Check completion, UTC | 2026-10-16T10:33:10.438337+00:00 | 2026-10-16T10:33:35.153777+00:00 |
| Passed checks | 23 | 23 |
| Mapped triples | 28,470 | 299 |
| Graph comparison | No missing or extra RDF terms | No missing or extra RDF terms |
| Answer comparisons | Six queries equal across SQL/reference RDF/mapped RDF/Ontop | Same six comparisons pass |
| Mapped SHACL | 0 violations, 5 warnings; gate passes | 0 violations, 3 warnings; gate passes |
| Low-score freshness | 90 → 89 live; old snapshot 90; refreshed 89 | 2 → 1 live; old snapshot 2; refreshed 1 |
| Demo restoration | Original teaching database fingerprint restored | Original teaching database fingerprint restored |

Full [report](../outputs/integration/runs/99568e1cd42b46aa8ddf05ac6d075a5b/report.html), [summary](../outputs/integration/runs/99568e1cd42b46aa8ddf05ac6d075a5b/summary.json), [PROV-O](../outputs/integration/runs/99568e1cd42b46aa8ddf05ac6d075a5b/provenance.ttl) and [provenance verification](../outputs/integration/runs/99568e1cd42b46aa8ddf05ac6d075a5b/provenance-check.json). Fixture [report](../outputs/integration/runs/75d6a50e89424e6fa9872844093196e9/report.html), [summary](../outputs/integration/runs/75d6a50e89424e6fa9872844093196e9/summary.json) and [PROV-O](../outputs/integration/runs/75d6a50e89424e6fa9872844093196e9/provenance.ttl). The mapped graph's nested SHACL run is `478addc17f0c4be5813c7d00da5a4cb3`; it has its own [validation provenance](../outputs/integration/runs/99568e1cd42b46aa8ddf05ac6d075a5b/shacl/provenance.ttl).

### How the integration provenance is recorded

**Entities:** fingerprints identify the six CSV inputs, reference graph, R2RML mapping, database DDL, RDFS schema, SHACL shapes, source code, question files, declared dependencies and runtime download manifest. A separate entity identifies the actual database rows through a deterministic content hash. The connection description records host, port, database and schema; it excludes credentials.

**Activity:** a unique integration run records its actual start and check-completion timestamps. The PROV activity end time also includes report assembly. Results are stored in `outputs/integration/runs/<run-id>/`; the stable HTML landing page and latest-success pointer select the newest successful run. Failed attempts remain separate and cannot masquerade as successful evidence.

**Agent and outputs:** the runner is identified by its code fingerprint, with the tested Python package versions. `prov:used` links the activity to input entities; `prov:wasGeneratedBy` links answer files, generated SQL, RDF, comparisons and reports to it. `provenance-check.json` independently re-reads those links and compares input/output hashes. The nested SHACL activity supplies the validator's own evidence. These are file/database-state records, not per-triple source-line annotations.

Versions: PostgreSQL 16 container; Morph-KGC 2.10.0; Ontop 5.5.0; PostgreSQL JDBC 42.7.13; RDFLib 7.6.0; pySHACL 0.40.1; SQLAlchemy 2.0.54; psycopg2-binary 2.9.13. M2ENV was retained; Morph was installed without replacing its existing dependencies. Runtime download URLs and locally computed fingerprints are captured in the snapshot. Docker's `16-alpine` tag and some transitive Python dependencies can change; the version declarations are not a bit-for-bit lock of every future machine. Download hashes are local evidence, not publisher signatures.

### Interpretation and limits

The shared mapping produces asserted facts only. The graph comparison preserves RDF identity and datatypes, with documented lexical normalization; the observed raw difference is also zero. Virtual query answers are compared as multisets. No full OWL ontology is passed to Ontop; the existing HermiT results are separately preserved. The activity extension remains excluded.

Shared table locks hold baseline comparisons to one database state. The intentional update runs in a separately loaded demo schema and restores its edited score; before/after artifacts are teaching states. A prior successful SHACL snapshot does not certify arbitrary future database updates. Freshness results demonstrate the distinction between live access and a saved graph, not general performance superiority.

The [new integration CI workflow](../.github/workflows/integration.yml) repeats the 23-check fixture procedure with a PostgreSQL service and uploads diagnostic artifacts. It is **prepared locally; no remote integration run is recorded**. Your earlier SHACL success screenshot belongs to the separate SHACL workflow. Neither record establishes branch-protection settings.

The [walkthrough](project-walkthrough.html#16-session-5-one-mapping-two-ways-to-answer) explains actual implementation failures and fixes: positional fingerprint sorting, nullable-score emission and Windows URI paths. The [README](../README.md#13-session-5--postgresql-mappings-materialization-and-virtualization) gives the full run sequence.


## 13. Session 6 learning provenance

This extension reads the mapped RDF from the later successful Session 5 source **`outputs/integration/runs/7c0b60e5ae2b4e7da058f851b1c8286c/oulad-mapped.nt`**. That source is selected through the latest-full receipt and checked against its graph hash and current selected CSV fingerprints. Earlier Session 5 runs listed above remain dated evidence; they are not relabeled as this later source run.

The learning activity **`f7649738f7414536bc2395ef7496eebf`** began **2026-10-17T21:32:30.408391+00:00** and completed checks **2026-10-17T21:33:16.413705+00:00** (UTC). The documentation was updated on **18 October 2026**. The PROV end time additionally includes report assembly. See the [run report](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/report.html), [summary](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/summary.json), [manifest](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/manifest.json), [PROV-O record](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/provenance.ttl) and [independent verification](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/verification.json).

### Inputs, transformations and software

Input entities identify the selected mapped graph and its receipt, the six selected CSV files, RDFS schema, fixed learning protocol, source scripts and evidence verifier by SHA-256. The graph builder reconciles labels and features independently with CSV joins. It saves a separate label-free day-60 graph, a label table and explicit train/test row lists.

The outcome models train on 335 eligible 2013J enrollments and test on 340 eligible 2014J enrollments, with no shared students. Twenty-six eligible earlier records were purged because their students occur in the future offering. Forty-seven already-withdrawn enrollments were excluded from the day-60 task. The original 748 enrollments, 531 successful and 217 unsuccessful outcomes remain unchanged. Test predictions are compared with **87 actual positive outcomes**, not the full historical count.

Imputation, constant-feature removal and scaling are fitted on training rows only. Grade values and inferred outcome classes are excluded. The preliminary prototype was corrected to remove zero-variance training features; the final run and code hashes above identify the corrected implementation. The three seeds and all model settings are retained. No source labels or historical facts were replaced by predictions.

The link task masks the 3,107 nonbanked historical submission links into 2,487 train, 310 validation and 310 test edges for each of three seeds. Supporting triples provide only offering membership and assessment types. Hidden target edges and their record-node paths are absent from training. Filtered truth is used for evaluation only; the count baseline uses training frequencies. It is a reconstruction task, separate from the temporal outcome task.

The software agent is identified by the learning runner's hash. Versions are torch 2.8.0, torch-geometric 2.8.0.post1, pykeen 1.11.1, scikit-learn 1.7.2, rdflib 7.6.0, pandas 2.3.3, numpy 2.3.5, matplotlib 3.10.0. The existing **M2ENV** was retained; no package installation was needed. Runtime caches are isolated under ignored `.runtime/learning/`. This records the observed versions, not a guarantee of bit-for-bit numerical identity across every machine.

### Results and evidence strength

- **21 learning checks passed:** original counts, CSV feature reconciliation, eligibility, banked/cutoff rules, exclusion of labels and future events, temporal separation and stable input hashes.
- **54 evidence checks passed:** recomputed predictions/metrics, training-only preprocessing, disjoint link partitions, train-count popularity ranks and candidate filtering, input/output fingerprints and PROV-O links.
- **Temporal average precision:** logistic regression 0.526; GraphSAGE mean 0.502 over three seeds; early-submission count 0.444; constant score 0.256.
- **Link reconstruction:** popularity beats TransE on all three splits under both ranking modes. Full ranks and candidate-set sizes are retained; filtered scores alone are insufficient.

`prov:used` connects the activity to input entities; `prov:wasGeneratedBy` connects features, labels, predictions, checkpoints, rank tables, figures and reports to the activity. `prov:wasAssociatedWith` identifies the software. The manifest excludes itself and the repeatable verification file to avoid self-referential fingerprints; the verifier records the manifest fingerprint it checked. Checkpoints are locally saved but `.pt` files are ignored by Git. A fresh clone must regenerate them before complete output-hash verification.

The current [project snapshot](provenance-snapshot.json) incorporates new evidence and refreshes listed file hashes. The [previous snapshot](history/provenance-snapshot-2026-10-16T103610Z.json) is preserved. Older audits and preliminary run folders retain their own dates and hashes; current code need not match every historical prototype. This is run/file provenance, not per-prediction causal explanation or a complete immutable code archive.

The current learning suite is local. This update adds no learning CI workflow and makes no claim that GitHub ran the models. Existing SHACL and integration workflows have their own scope and evidence. No commit or push was performed for Session 6.

The [detailed learning explanation](learning-results-explained.html) records the cohort changes, metrics, failure modes, actual fixes and limitations. The [README](../README.md#14-session-6--learning-and-baseline-comparisons) gives all steps. This is a teaching experiment on one module and one future offering, with date-based availability assumptions and uncalibrated scores, not a deployed student decision system.

## 14. Session 7 access provenance

The access activity **`dd0223f4396343f48a214657557b40aa`** reads `data/processed/oulad.ttl` and `ontology/education.rdfs.ttl`. These are the existing asserted facts and RDFS schema, not the separate OWL inference output or Session 6 predictions. It uses the course Session 7 architecture with OULAD-specific examples, questions, interpretation rules and independent CSV answers. The original course scripts remain unchanged.

This live **record-mode** run started **2026-10-18T12:25:42.707752+00:00** and completed its evaluation loop **2026-10-18T12:28:23.320689+00:00** (UTC), before report/manifest assembly. Model **gemini-3.5-flash-lite**, **39 API requests**, within the user-approved maximum of 45. The existing lab key was read from its configured file without copying it into the project. Credentials and raw provider error bodies are absent from the saved evidence. The project `.env.access` option is ignored by Git.

Input fingerprints cover the asserted graph, schema, six selected CSV tables, examples, held-out questions, domain prompt, access code and verification script. Each run's VoID/schema files describe the actual queried snapshot. Reference SPARQL answers must agree with separate pandas calculations before model generation starts. The ten answerable questions and three refusal cases are distinct from the eight prompt-example questions. Their authored wording is held out, not their entire domain; some related operations occur in both sets.

The cache and `model-calls.json` retain genuine responses, model identity, prompt key, timestamp and provider-reported token usage. Exact prompt keys include the chosen model and prompt text, which includes data/schema fingerprints. `answers.json` links each question/setting to attempted queries, diagnostics, returned rows and its score. The source prompt and deterministic retrieval logic reconstruct prompt context for the corresponding source version. A replay reuses these responses and is explicitly labeled replay; it must not be counted as fresh live model performance. The instructor's Brunel cache was never used as OULAD evidence.

A full replay **`2d48629d7cdb4587a89ec083344283ca`** subsequently completed with **0 API requests**; see its [report](../outputs/access/runs/2d48629d7cdb4587a89ec083344283ca/report.html). The latest-evaluation pointer now identifies that replay. The live run above remains the source of model-performance claims. The 39 live responses are retained individually; the response cache has 26 unique keys because examples and repair share the same initial prompts. For repeated prompt keys the latest recorded response is retained in the cache.

| Setting | Mean row F1 | Exact answers | Correct refusals | Successful repairs |
|---|---:|---:|---:|---:|
| schema | 1.000 | 10/10 | 3/3 | 0 |
| examples | 1.000 | 10/10 | 3/3 | 0 |
| repair | 1.000 | 10/10 | 3/3 | 0 |


All three settings answered all ten questions exactly and refused all three missing-data questions. Examples and repair therefore showed **no measured accuracy improvement on this benchmark**. No live repair was needed; its behavior was verified separately with deliberately faulty, scripted responses. This is a ceiling result on a small, straightforward test, not evidence that every natural-language question will work.

The run has **65 passing local/evidence checks**. Local fault-injection tests establish repair behavior and read-only limits, while the live report establishes model behavior on this question set. Correct missing-data refusals are distinct from invalid queries and provider failures. The row-aware score preserves associations that flattened value sets can lose; both scores are retained. All counts remain historical observations, not causal explanations or newly predicted facts.

[Run report](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/report.html), [summary](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/summary.json), [answer records](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/answers.json), [manifest](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/manifest.json), [PROV-O](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/provenance.ttl), [verification](../outputs/access/verification.json).

The PROV-O activity uses fingerprinted input entities through `prov:used`, and its output entities link back through `prov:wasGeneratedBy`. The manifest fingerprints the generated run files, including the PROV file; it excludes itself to avoid a circular digest. Code hashes and package versions identify the implementation; no claim is made that this is an immutable archival copy of every source version. A later edit requires a fresh run or leaves an older run as dated historical evidence.

The current [project fingerprint snapshot](provenance-snapshot.json) preserves the [previous audit](history/provenance-snapshot-2026-10-17T213713Z.json) and adds the access code, documentation and actual run evidence. Earlier Session 5/6 results retain their dates; they were not rerun for this extension. The local checks ran in **M2ENV** using rdflib 7.6.0, pyoxigraph 0.5.11, requests 2.34.2, pandas 2.3.3, PyYAML 6.0.3. No package installation, new Conda environment, Git commit or push was performed for Session 7. No new Session 7 CI workflow or remote execution is claimed.

See the [Session 7 explanation](access-results-explained.html) for detailed interpretation and challenges, and the [README](../README.md#15-session-7--natural-language-access) for reproduction and browser instructions.

### Interface refresh and coverage audit — 19 October 2026

This update changed the web presentation and added `src/access/ui/index.html`, `style.css` and `app.js`. The server renders those local assets with counters from the observed graph and the existing example questions. The source inventory now includes the UI assets. The data, vocabulary, prompt, question benchmark and model-generation logic were not changed.

The new replay activity **`6316669854314620a77b7fa0baedf9cd`** completed with **zero API requests** and the same recorded-answer scores: 10/10 exact factual answers and 3/3 correct refusals in each setting. See [the replay report](../outputs/access/runs/6316669854314620a77b7fa0baedf9cd/report.html), [manifest](../outputs/access/runs/6316669854314620a77b7fa0baedf9cd/manifest.json) and [PROV-O](../outputs/access/runs/6316669854314620a77b7fa0baedf9cd/provenance.ttl). The current latest-evaluation pointer now identifies this replay, superseding the earlier pointer described above. The first live record remains the evidence for the provider's measured performance; its code fingerprints refer to its historical version, not this UI revision.

All **65 local/evidence checks passed**. Browser checks covered 1440, 768 and 390-pixel layouts, example selection, answer 383/365, tabs, the dataset dialog, unsupported-input recovery and CSV export. These tests used catalog mode, without provider calls. See [the interface verification receipt](../outputs/access/interface-verification.json). The reviewed preview used port 8008 after the original port-8007 page remained stale; this does not change the script's default port.

The [coverage audit](course-coverage-audit.html) compares the actual project with the supplied Session 8 lecture and defense/lab documents. It distinguishes implemented layers from missing entity-resolution evaluation, reproducible deployment, startup validation enforcement and the final report/open-problem requirement. It does not claim that those gaps have been implemented or that the instructor has awarded a grade.

The [previous project snapshot](history/provenance-snapshot-2026-10-18T204947Z.json) is retained; the current inventory is refreshed for this UI revision and its replay. No new packages, API charges, Git commit, push or new CI workflow were introduced.
