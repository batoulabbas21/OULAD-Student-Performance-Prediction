# OULAD project provenance

**Where the data came from, what we changed, and why the results can be traced.**

Prepared on **13 October 2026** for the `kr-oulad` project. This guide describes the current AAA build and links to its evidence. Start here for the project's origins; use the [README](../README.md) for commands.

> **Provenance means the history behind a result.** For this project, it connects an original CSV row to its RDF representation, the ontology definition applied to it, and the resulting answer.

## 1. The project in one minute

The project turns a small, understandable part of OULAD into a knowledge graph. It keeps student identity separate from enrollment in a particular offering, answers questions with SPARQL, and uses OWL reasoning to classify records.

| Current scope | Recorded result |
|---|---|
| Selected module | AAA, across offerings 2013J and 2014J |
| People and participation | 712 distinct student IDs; 748 enrollments |
| Assessment data | 12 assessments; 3,149 assessment records |
| Learning resources | 413 resource descriptions |
| Asserted RDF | 28,470 data triples, with a separate 105-triple RDFS schema |
| OWL results | 6,119 additional named type assertions |
| Saved verification | 14 core checks and 17 ontology checks passed |

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

The workflow adapts the local KRR labs: Session 1 for profiling, Session 2 for RDF/RDFS, SPARQL and graph access, and Session 3 for ontology imports and reasoning. Session 3 references include [local_reasoner.py](../../KRR/demos/session-03-ontology/local_reasoner.py), [check_my_axioms.py](../../KRR/demos/session-03-ontology/check_my_axioms.py), and [realize_sample.py](../../KRR/demos/session-03-ontology/realize_sample.py).

The OULAD model, scripts and explanations were developed for this project with Codex assistance. The education classes and rules are project modeling choices; the source dataset does not supply this ontology. A project-wide code license has not been established. The dataset and FOAF licenses apply to their respective material.

## 3. The journey from CSVs to answers

**Download → select AAA → profile → create RDF → add ontology definitions → reason → inspect and verify.**

| Stage | What happens | Main evidence |
|---|---|---|
| Download | `fetch_data.py` retrieves the seven original CSV tables and records their fingerprints. | [Raw manifest](../data/raw/manifest.json) |
| Select | `select_subset.py` keeps AAA's two offerings and their related rows. Assessment records are selected through assessment IDs. | [Selection settings and counts](../data/interim/selection.json) |
| Profile | `profiling.py` reports distributions, missing values, keys and relationships for the selected scope. | [Subset profile](../outputs/profiling/subset/profile.html) |
| Convert | `convert_to_rdf.py` maps selected rows to stable identifiers, links and typed values using the authored RDFS vocabulary. | [RDF facts](../data/processed/oulad.ttl) and [graph summary](../data/processed/graph_summary.json) |
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
- **Ontology axioms and data checks have different jobs.** RDFS domains/ranges infer types. OWL uses open-world reasoning: a missing link alone is not a required-field violation. Python checks assess the supplied records; SHACL validation remains a later stage.

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
| This provenance audit | 13 October 2026, 13:05:14 | Read-only inspection and fingerprint comparisons |

The audit checked **all seven raw CSVs** against the manifest. It also checked the four input fingerprints stored by the full reasoner report, and the two stored by the Fuseki report. All matched the current files.

The accompanying [provenance-snapshot.json](provenance-snapshot.json) records full SHA-256 fingerprints for 72 selected data, code, ontology and result files. A fingerprint helps detect file changes; these local fingerprints are not publisher-authenticated signatures. They capture the files inspected now, not an independently archived history of every earlier run.

The current environment is the existing Conda **M2ENV**: Python 3.12.15, pandas 2.3.3, RDFLib 7.6.0, owlrl 7.6.2 and Owlready2 0.51. The snapshot includes additional notebook and profiling package versions. This inventory describes the environment inspected now. The [README](../README.md) contains the execution order, Java requirement, ontology steps and optional database instructions.

After changing data, mappings or axioms, regenerate their dependent outputs and verification reports before updating this guide. Reordered Turtle serialization can change a file's fingerprint even when its RDF meaning is unchanged.

## 10. Connection to the course provenance lesson

The [W3C PROV-O model](https://www.w3.org/TR/prov-o/) describes provenance using entities, activities and agents. Here is how those ideas fit this project:

| PROV idea | Plain meaning | Project example |
|---|---|---|
| Entity | An input or output | A CSV, the RDF graph, an ontology file or an answer table |
| Activity | Work that uses or produces entities | Subsetting, conversion, querying or reasoning |
| Agent | A person, organization or program responsible for work | Dataset authors, the project modeler or the conversion program |
| Derivation | An output depends on an input | The inferred types depend on the asserted RDF and ontology |

This guide and its snapshot provide **documented file-level provenance**, plus one checked row-to-inference example. They do not add `prov:wasDerivedFrom` annotations to every RDF fact or create a complete machine-queryable run history.

The course's [Session 4 add_provenance.py](../../KRR/demos/session-04-shacl/add_provenance.py) demonstrates a separate PROV-O graph. Extending this project in that direction would require explicit run identifiers and links between source entities, transformations and outputs. That extension has not been implemented by writing this guide.

## 11. What this record cannot establish

The selected AAA offerings are a teaching scope. Results do not describe all university students, reveal the real module title, or establish causal explanations of performance. Missing activity and unknown values remain limits on the questions that can be answered.

The project has not recorded a complete immutable history of each past code version, exact execution start/end times, or provenance for every triple. Some stages have only saved reports and current source files. This guide states those limits so its evidence can be used at the level actually supported.

**To explain the project aloud:** “We obtained OULAD from UCI, preserved the originals, selected AAA and checked its tables. We mapped the selected records into RDF, authored an education ontology with a small attributed FOAF fragment, and used HermiT to derive classifications. We compared the graph answers and inferred identities with the CSVs. The manifests, source files and verification reports let us trace those results back to their inputs.”
