# First verified core run

Date: 2026-10-10 (Asia/Beirut).
Environment: existing M2ENV, Python 3.12.15; pandas 2.3.3, rdflib 7.6.0, owlrl 7.6.2.
No environment or course-lab files changed.

## Scope and observed counts

Selected module AAA, both available offerings. Core tables and resource metadata only.

| Measure | Observed |
| --- | ---: |
| Offerings | 2 |
| Enrollments | 748 |
| Assessments | 12 |
| Assessment records | 3,149 |
| Resource descriptions | 413 |
| Asserted RDF triples | 28,470 |
| Records after recorded deadline, banked excluded | 815 |
| Records with score below 40 | 90 |
| Existing assessment records with unknown score | 3 |
| Assessments with unknown deadline | 2 |

The profile's implemented error checks found no violations in the subset.
The two nonzero warning checks were missing scores and missing deadlines.
This does not prove that every possible semantic rule holds.

## Verification

All 14 verification checks passed. These cover entity counts, enrollment counts by offering,
assessment subtype inclusion, exact late-record identities and days versus an independent SQL query,
low and missing score counts, outcomes by offering, preservation of unknown values,
same-day/banked lateness boundary cases, and a bounded RDFS inference demonstration.

## Limits

- Student activity is downloaded but not mapped in the core build; its query is explicitly unavailable.
- RDFS reasoning was demonstrated on a small selected sample, not materialized over the entire graph.
- SHACL, OWL modeling beyond RDFS, R2RML, learning, and an LLM access layer are future stages.
- Follow-up questions listed as extensions in the question guide are not yet implemented queries.
- These are descriptive results for a selected module, not causal explanations or evaluated predictions.

See README.md for reproduction commands. Generated details are in outputs/ and data/processed/.

## Neo4j extension verified on 2026-10-11

The existing lab Neo4j service was started and the RDF property-graph projection loaded under label OULAD.
The imported core snapshot contains 5,037 nodes and 8,221 relationships. Cypher reports 815 late records,
matching SPARQL. Its 712 Student nodes represent distinct IDs, separate from the 748 Enrollment nodes.
No graph deletion was performed. The importer retains old snapshots and points queries at the current one.
Neo4j's displayed general class labels are added explicitly by the importer from the RDFS subclass hierarchy;
the server is not being treated as an RDFS reasoner.

## Fuseki extension verified on 2026-10-12

The project Compose override reuses the course's Fuseki 5.5.0 image, port 3030, and persistent
data volume. The startup configuration keeps `/kr` at `/data/kr` and adds `/oulad` at `/data/oulad`.
Course source files and the Conda environment were not changed.

The OULAD default graph contains 28,575 triples: 28,470 RDF facts and 105 RDFS schema triples.
The loader fetched the uploaded graph and checked graph equivalence with the local graph.
All six available SPARQL query result sets matched RDFLib, ignoring row order but retaining duplicates:

| Query | Returned rows |
| --- | ---: |
| Enrollments by offering | 2 |
| Assessments | 12 |
| Late records | 815 |
| Low scores | 90 |
| Outcomes by offering | 8 |
| Unknown scores | 3 |

The activity query is marked unavailable for this core build. No automatic RDFS inference is enabled.
An identical second load reported `unchanged`. After restarting the container, `--check-only`
passed again and the Fuseki UI returned HTTP 200. The lab `/kr` count was 135,841 before the
project setup, after import, and after restart.

Reproduction commands and browser queries are in README section 10. The most recent verification
record and live query CSVs are in `outputs/fuseki/`. Changed default-graph imports are designed to
save the prior nonempty graph there before replacement; that replacement path was not exercised
on the unchanged core data.

## OWL ontology extension verified on 2026-10-13

Session 3 was adapted using RDFLib, Owlready2 0.51 and its HermiT reasoner with the existing
M2ENV and JDK 21. No Protégé setup, package installation or course-source change was needed.

The authored OWL extension retains the project's IRIs and imports generated OWL declarations
from the existing RDFS schema plus a documented FOAF Person/Agent fragment. The unchanged
official FOAF snapshot and its attribution are stored under `ontology/imports/`. This fragment
is not the full FOAF ontology and does not claim a BFO alignment.

The clean ontology plus all 28,470 asserted AAA data triples is consistent, with no unsatisfiable
named class. The run classified 5,037 named individuals and exported 6,119 new named type assertions.
This is a limited type export, not the entire OWL closure. Exact inferred identities were reconciled
against the selected CSV records:

| Derived class | Named individuals |
| --- | ---: |
| SuccessfulEnrollment | 531 |
| WithdrawnEnrollment | 126 |
| LowScoreAssessmentRecord | 90 |
| BankedAssessmentRecord | 42 |
| NonBankedAssessmentRecord | 3,107 |
| EnrollmentWithLowScore | 75 |

All 17 checks in `evaluation/verify_ontology.py` passed, including the full-data identities,
published Person typing, real-sample fidelity, domain mistakes, unsatisfiable versus inconsistent,
missing links, identity/cardinality, the 39/40/41/missing score boundary, EquivalentTo versus
SubClassOf, and some versus only. Synthetic cases stay separate from real source facts.

The selected teaching sample contains 7 enrollments, 51 individuals and 279 retained source triples.
Its own reasoning run adds 65 named type assertions. The executed results notebook and its HTML
export show both real examples and the semantic test outcomes. The notebook reads existing
reasoner evidence, checks source hashes and runs local SPARQL; it does not rerun HermiT or update
the database services. See README section 11 for reproduction and modeling details.
