# First verified core run

Date: 2026-10-10 (Asia/Beirut).
Environment: existing M2ENV, Python 3.12.15; pandas 2.3.3, rdflib 7.6.0, owlrl 7.6.2.
No environment or course-lab files changed.

## Scope and observed counts

Selected module AAA, both available offerings. Core tables and resource metadata only.

| Measure | Observed |
|---|---:|
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
