# Understanding the OULAD project

**What we built, what the results mean, and how we handled challenges and errors.**

Prepared on **14 October 2026**, updated through Session 5 on **16 October 2026**. This guide explains the saved earlier stages and the newly executed PostgreSQL integration. Section 16 covers mappings, materialization, virtualization, results and actual fixes.

> **The main result:** we have a traceable education knowledge graph, an ontology that derives useful classifications, and a validation gate that catches structural errors while retaining documented missing values. The current full SHACL report has **0 violations and 5 warnings**, and **37 verification checks pass**.

## 1. What problem are we solving?

OULAD originally consists of separate CSV tables. A question such as “Which enrollments have a low assessment score?” requires joining student, offering, enrollment and assessment information correctly.

Our project represents these relationships explicitly, gives them clear meanings, and checks that the resulting graph follows our rules. It applies the lab techniques to education data while retaining the existing **M2ENV** Conda environment and the agreed project folders.

We selected module **AAA**, an anonymized Social Sciences module, across **2013J and 2014J**. A presentation is one offering of a module. AAA's real title, assignment content and instructors are not provided. The [AAA explanation](aaa-module.md) contains the detailed source interpretation.

Three different questions guide the work:

| Question | Tool or layer that answers it |
|---|---|
| What is explicitly recorded? | CSVs, RDF facts and SPARQL |
| What follows logically from those facts and our definitions? | RDFS/OWL and the reasoner |
| Does the supplied graph satisfy explicit data requirements? | SHACL and the project gate |

An enrollment can be logically consistent in OWL while failing a SHACL completeness check. These layers have different purposes.

## 2. What we did, in order

| Stage | Work completed | Why it matters |
|---|---|---|
| Download | Retrieved the seven OULAD CSVs and recorded source information, sizes and SHA-256 fingerprints. | We can identify the original inputs and detect later file changes. |
| Select | Kept AAA's two offerings and their related rows in separate interim files. | A small connected extract is easier to explain and validate. |
| Profile | Inspected distributions, missing values, candidate keys, references and value ranges. | Problems in source tables should be understood before conversion. |
| Model | Distinguished Student, Module, CourseOffering, Enrollment, Assessment, AssessmentRecord and LearningResource. | The graph respects the different meanings and identities in the data. |
| Convert to RDF | Created stable identifiers, links and typed values from the selected tables. | Questions can follow explicit relationships instead of repeatedly reconstructing joins. |
| Add RDFS | Declared classes, subclasses, domains and ranges. | The vocabulary becomes interpretable and supports basic entailment. |
| Query and verify | Answered competency questions and compared graph answers with CSV/SQL results. | We checked that the conversion preserves the intended answers. |
| Add database views | Loaded a property-graph projection into Neo4j and RDF/schema into Fuseki. | The same data can be explored visually and queried through a server. |
| Add OWL | Authored formal class definitions, reused a small FOAF fragment and ran HermiT through Owlready2. | The ontology can classify records and expose contradictory modeling commitments. |
| Add SHACL | Defined explicit graph constraints, review warnings, target checks and a blocking gate. | The pipeline can reject malformed data rather than merely describe its meaning. |
| Record provenance | Wrote the human-readable guide, fingerprints and PROV-O records for SHACL and integration runs. | Results can be connected to their inputs, software and activity. |
| Add Session 5 integration | Loaded PostgreSQL and reused one R2RML mapping with Morph-KGC and Ontop. | Saved and virtual graphs preserve the existing questions; committed changes demonstrate freshness. |

The current main pipeline places SHACL **immediately after RDF conversion and before answering questions**. Neo4j, Fuseki and full OWL reasoning remain explicit separate steps. The full command sequence is in the [README](../README.md).

## 3. What data do we actually have?

| Measure | Result | Correct interpretation |
|---|---:|---|
| Modules | 1 | The selected module is AAA. |
| Offerings | 2 | The same module is offered in two presentations. |
| Distinct student IDs | 712 | Count of different recorded people. |
| Enrollments | 748 | Count of participation records, each tied to one offering. |
| Assessments | 12 | Ten tutor-marked assessments and two exam definitions. |
| Assessment records | 3,149 | Recorded student-assessment results, including banked results. |
| Resource descriptions | 413 | Descriptions of available resources, not evidence that each was accessed. |
| Asserted RDF triples | 28,470 | Explicit statements produced by conversion. |
| Separate RDFS triples | 105 | Vocabulary statements describing classes and properties. |

**Why are there 748 enrollments but only 712 students?** Thirty-six student IDs appear in both offerings. A student is therefore a different entity from an enrollment. A repeated student may have a different outcome in each offering.

The seven types of project entities above account for **5,037 named entities** in total. This explains the corresponding Neo4j node count and the number of individuals classified in the full ontology run. A node can have many triples and several class memberships, so these counts need not equal the number of triples or inferred types.

Daily interaction data were downloaded but excluded from the core graph. The optional activity query is marked **unavailable**. That status does not tell us whether the students studied or clicked resources; it tells us those facts were not loaded.

## 4. How to read the graph

The main relationship pattern is:

```text
Enrollment --hasStudent--> Student
Enrollment --inOffering--> CourseOffering --offeringOf--> Module
AssessmentRecord --recordForEnrollment--> Enrollment
AssessmentRecord --forAssessment--> Assessment --assessmentInOffering--> CourseOffering
LearningResource --resourceInOffering--> CourseOffering
```

The record for student `100893` in AAA/2013J is identified by:

```text
https://example.org/oulad/id/enrollment/AAA/2013J/100893
```

Its recorded final result is Pass. This fact belongs to that enrollment. We do not turn it into a timeless statement that the person always passes.

The RDF mapping preserves several distinctions:

- Identifiers are strings or IRIs, rather than quantities to average.
- Scores are decimal values and banked flags are Booleans.
- Day values are signed integer offsets relative to the offering, so a negative registration day is meaningful.
- A missing optional value produces no property assertion. It is not replaced by zero, false or the text `nan`.
- A banked assessment result can come from an earlier presentation. `AssessmentRecord` is therefore a more accurate name than assuming every row is a fresh submission.

## 5. What the analytical answers mean

| Answer | Result | Interpretation and limit |
|---|---:|---|
| Enrollments in 2013J | 383 | Participation records for that offering. |
| Enrollments in 2014J | 365 | Participation records for the later offering. |
| Recorded late assessment records | 815 | Nonbanked records with both dates known and submission strictly after the recorded deadline. |
| Known scores below 40 | 90 | Low-scoring assessment records; multiple records may concern one enrollment. |
| Enrollments with at least one low score | 75 | Different enrollments associated with those 90 records. |
| Unknown scores | 3 | The records exist, but their marks are not supplied. |
| Banked assessment records | 42 | Results flagged as transferred from an earlier presentation. |

The 815 late records are not 815 different students. A same-day submission is excluded from “late,” and banked results are excluded. The result does not account for individual extensions or establish misconduct.

The 90 low scores do not imply 90 final module failures. A final outcome is recorded separately. If expressing the low-score proportion, the known-score denominator is **3,146**, giving **90 / 3,146 = 2.86%**. Including the three unknown scores in a “known score” denominator would be misleading.

Final outcomes are:

| Outcome | 2013J | 2014J | Both offerings |
|---|---:|---:|---:|
| Pass | 258 | 229 | 487 |
| Distinction | 20 | 24 | 44 |
| Fail | 45 | 46 | 91 |
| Withdrawn | 60 | 66 | 126 |
| Total | 383 | 365 | 748 |

Our definition of success is Pass or Distinction: **487 + 44 = 531 successful enrollments**. Using all enrollments, including withdrawals, the proportion is **531 / 748 = 70.99%**. It is 72.58% for 2013J and 69.32% for 2014J under the same definition. These describe this selected extract; they do not explain why the proportions differ.

Evidence: [enrollment answers](../outputs/answers/01_enrollments.csv), [outcomes](../outputs/answers/05_outcomes.csv), [late-record query](../queries/03_late_records.rq) and [ontology class counts](../outputs/ontology/inferred-class-counts.csv).

## 6. What the ontology added

RDFS provides the basic hierarchy. For example, a TutorMarkedAssessment is an Assessment, and a Student is a Person. OWL adds richer definitions and commitments, including disjoint classes, inverse properties, qualified cardinality and class equivalences.

The ontology aligns the project's Person class with a documented fragment of FOAF containing Person and Agent. It does not import every FOAF axiom or claim a complete BFO alignment.

| Inferred class | Count | Meaning |
|---|---:|---|
| SuccessfulEnrollment | 531 | Enrollment with recorded outcome Pass or Distinction. |
| WithdrawnEnrollment | 126 | Enrollment with recorded outcome Withdrawn. |
| LowScoreAssessmentRecord | 90 | Assessment record with a known score strictly below 40. |
| BankedAssessmentRecord | 42 | Record with the banked flag explicitly true. |
| NonBankedAssessmentRecord | 3,107 | Record with that flag explicitly false. |
| EnrollmentWithLowScore | 75 | Enrollment linked to at least one low-score record. |

For enrollment `AAA/2013J/100893`, the CSV supplies Pass, the RDF supplies the enrollment and its outcome, and the OWL definition supports classifying it as SuccessfulEnrollment. The inference follows from our definition and the existing fact; it is not a future prediction.

HermiT classified **5,037 named individuals** and the exporter saved **6,119 additional named type assertions**. These are extra classifications, not 6,119 new people or newly collected observations. The export is limited to named types and is not the complete OWL deductive closure.

The clean ontology and loaded facts are **consistent**, and no named class is unsatisfiable in the saved full run. Consistency means the axioms and facts can hold together under the model. It does not establish that the dataset is complete or that every modeling assumption is true in the real world.

All **17 ontology checks passed**, including exact inferred identities against CSV expectations and controlled semantic examples. See [ontology verification](../outputs/ontology/verification.json) and the [readable ontology results](../outputs/ontology/ontology-results.html).

## 7. What SHACL added

The shapes describe requirements for the supplied graph. Examples include exactly one Student link per Enrollment, a present score within [0,100], a Boolean banked flag, and agreement between the offering of an assessment and the offering of the corresponding enrollment.

We used SHACL Core for counts, datatypes, ranges, allowed values, forbidden properties, subtype alternatives and the comparison between registration and withdrawal dates on the same enrollment. SHACL-SPARQL handles checks across distinct records or linked paths, including duplicate contextual keys and cross-offering relationships.

The validator uses asserted RDF plus the RDFS hierarchy with automatic inference disabled. SHACL can still recognize subclasses for class targets and class checks. We avoid domain/range materialization because it could give an incorrectly typed object the very type we want to check explicitly.

There are **14 target-bearing shapes**. Thirteen have focus nodes in the core build. The optional DailyInteraction shape has none because activity was not loaded. The validator prints the counts, and the full verification compares seven structural entity counts with independent CSV-derived expectations.

### Reading a validation result

| Report field | Meaning | Example |
|---|---|---|
| Focus node | The entity under inspection. | `assessment-record/260355/1754` |
| Path | The property involved. | `edu:score` |
| Constraint | The requirement that produced the result. | `MinCountConstraintComponent` |
| Severity | The project's triage category. | Warning |
| Message | The interpretation or review action. | Keep the unknown score absent; do not replace it with zero. |

Open the [full HTML report](../outputs/shacl/full/report.html). The CSV and Turtle versions retain the detailed results for inspection or another tool.

### Why “conforms False” and “gate PASS” can appear together

The strict validator reports `conforms=False` when validation results are present, including warnings. Our pipeline makes a separate policy decision:

```text
No violations + no unknown severities + no empty required targets
    -> project gate passes
```

Warnings remain visible for review. A gate pass therefore means that the supplied graph meets our blocking requirements; it does not mean that the graph has no limitations or that every possible rule has been checked.

| Exit code | Meaning | What to do |
|---|---|---|
| 0 | Gate passes. | Read any warnings before interpreting the answers. |
| 1 | Gate fails. | Inspect violations and required-target coverage. |
| 2 | Execution error. | Check missing files, parsing, shapes or dependencies; no successful validation is established. |

After an execution error, an older report may still exist in the output folder. Check the command's exit code, report timestamp and run ID before treating that report as current.

## 8. The exact SHACL results and their interpretation

| Experiment | Scope | Violations | Warnings | Strict conforms | Gate |
|---|---|---:|---:|---|---|
| Full graph, triaged shapes | All 28,470 asserted facts plus schema | 0 | 5 | False | PASS |
| Real sample, triaged shapes | 299 unchanged source triples plus schema | 0 | 3 | False | PASS |
| Broken-link sample | Same sample with one Student link changed | 1 | 3 | False | FAIL |
| Naive first draft | Real sample; missing scores/deadlines treated as violations | 3 | 0 | False | FAIL |

The full graph's five warnings are:

| Focus node suffix | Missing property | Treatment |
|---|---|---|
| `assessment-record/260355/1754` | Score | Keep the record and its unknown mark. |
| `assessment-record/2606802/1760` | Score | Same treatment. |
| `assessment-record/721259/1752` | Score | Same treatment. |
| `assessment/1757` | Exact exam deadline | Keep the exam definition and leave the date unknown. |
| `assessment/1763` | Exact exam deadline | Same treatment. |

These exact identities match missing values in the selected CSVs. The sample has only three warnings because it contains one of the unknown-score records and both exam definitions.

The first draft and triaged sample use the **same data**. The change is the severity assigned to those three absences after reviewing their meaning. We did not delete the affected records or invent replacement values to make the report pass.

The broken sample changes the Student link on enrollment `AAA/2013J/100893` to an untyped teaching identifier. The resulting Class violation is expected. It demonstrates that a malformed relationship stops the gate while known completeness warnings remain visible.

The current full run took approximately **three minutes** on this machine. The small examples took about one second each in the latest saved run. Runtime depends on the machine and concurrent work; the cross-record SPARQL checks are more expensive than simple datatype or range checks.

## 9. Actual challenges and how they were addressed

This section records the challenges supported by the project files and implementation history. It is not a complete terminal transcript. Deliberate teaching faults are listed separately in the next section.

| Challenge or actual issue | Why it mattered | Response and remaining limit |
|---|---|---|
| Repeated students across offerings | A student ID alone cannot identify a participation record or its outcome. | Created contextual Enrollment IRIs using module, offering and student. Verified 712 people versus 748 enrollments. |
| Large daily-activity table | Including activity would substantially enlarge the first graph and distract from the core joins. | Retained the original download but left activity out of the core build. Its question is explicitly unavailable. |
| Missing scores and exam dates | Imputing zero or a date would invent facts and distort queries. | Preserved absence, kept the records and recorded warnings. This documents the limitation; it does not recover missing values. |
| Exam definitions without exam result records | A defined exam is not evidence that every student's result is available. | Modeled assessments separately from assessment records. No rule requires an exam mark for every enrollment. |
| Banked results and lateness | A banked result is not necessarily a new submission in that offering. | Required `isBanked=false` for the late-record query, with both dates known. |
| Negative day values | Treating all negative numbers as errors would reject valid pre-start registration/activity. | Kept signed integer offsets and tested negative-day examples. |
| Assignment and exam weights | Summing both groups could appear to produce an invalid 200% total. | Validated individual percentages; did not invent a formula combining the separate weighting schemes. |
| Confusing inference with validation | RDFS domain/range statements can add types rather than reject a bad link. OWL can permit unstated fillers. | Retained reasoning for meaning and added explicit SHACL constraints for supplied data. Validation disables domain/range materialization. |
| FOAF import compatibility warning | Loading the full vocabulary through Owlready2 raised a property-kind warning for `foaf:name`. | Cached the original, documented the issue and imported only the relevant Person/Agent fragment. Results apply to that selected fragment. |
| Windows ontology-loading path handling | Owlready2's `file:///C:/...` handling was problematic for the loader. | Serialized the merged graph to N-Triples and loaded a `BytesIO` file object, as documented in the reasoner code. |
| Enumerating RDF instances in Owlready2 | RDF class assertions need not explicitly declare `owl:NamedIndividual`. | Added declarations to a temporary loading graph so the reasoner can enumerate instances. Original source facts remain unchanged. |
| Local ontology imports | A missing or unresolved import could change the knowledge available to the reasoner. | Used a local catalog and fail when an import is absent from it. Retained the FOAF snapshot and fingerprints. |
| Fuseki dataset creation rejected by the lab admin interface | The browser/admin creation route was unavailable under the lab configuration. | Added `/oulad` through a project startup configuration while preserving `/kr` and the persistent volume. Import, query parity and restart persistence were checked. |
| Different graph representations | Neo4j labels/properties, RDF triples and OWL class memberships do not have identical counts or semantics. | Imported a documented property-graph projection, retained IRIs and compared shared answers. Inherited labels are added explicitly by the importer. |
| A report could “pass” while targeting nothing | A misspelled class name can yield zero focus nodes and strict SHACL conformance True. | Added a project coverage gate and a deliberate zero-target test. Full verification also checks source-derived counts. |
| A record could lose its type triple | Class-only targeting might fail to inspect that record. | Added property-based targets alongside class targets, with explicit class requirements; tested a missing-type record. |
| Known source gaps versus blocking errors | Treating all missing values as violations made the naive sample fail without identifying malformed numbers or links. | Separated completeness warnings from structural/value violations, documenting each triage choice. |
| Zero could disappear from the readable result | An early value-extraction expression treated numeric zero like an absent value. | Replaced truthiness handling with an explicit `None` check. A test now confirms that an invalid zero offering length is reported with value `0`. |
| Slow full-graph validation | Repeated cross-record queries take much longer than small-example checks. | Kept a complete local gate and a small real-data fixture for fast practice/CI. Recorded runtimes rather than hiding the cost. |
| Reports can become stale after rerunning a stage | A new run changes timestamps, run IDs and output fingerprints, even if the data and result counts stay the same. | Verification checks the exact full-report fingerprint and current inputs. Rerun verification after validation; preserve output folders if earlier runs are needed. |
| Fields not represented in RDF | SHACL cannot inspect studied credits or resource week ranges absent from the mapping. | Kept those checks in Python profiling and documented the SHACL coverage boundary. |
| Source duplicates can collapse during conversion | RDF is a set of triples; repeated source rows can become indistinguishable after mapping to the same IRI. | Kept source key/duplicate checks before conversion and graph key checks across distinct nodes afterward. |
| Remote CI is a separate step | A local workflow file does not prove a GitHub run passed or prevent merging by itself. | Your screenshot shows the SHACL workflow succeeded at `afd8535` on main. The new integration workflow is prepared locally; branch protection remains a separate repository setting. |

The current issues that remain are primarily **documented missingness and scope limitations**. There is no outstanding blocking SHACL violation in the saved full graph. That statement concerns the implemented constraints, not every conceivable defect.

## 10. Deliberate errors: what we tested and learned

These are controlled examples, not errors found in real student records. The broken fixture and synthetic examples stay separate from the original data and database imports.

### Ontology experiments

| Deliberate setup | Expected outcome | Lesson |
|---|---|---|
| Use `hasStudent` as though its subject were a Student, while its domain is Enrollment and Person/Enrollment are disjoint. | The two constructed teaching classes are unsatisfiable. | Domains infer types, and those inferred types can conflict with disjointness. |
| Create an instance of one of those impossible classes. | The example ontology becomes inconsistent. | An empty impossible class differs from an asserted impossible individual. |
| Omit explicit Student/Offering links from an enrollment constrained by OWL exactly-one axioms. | The example remains consistent. | Open-world reasoning can allow unstated fillers. |
| Give one enrollment two student names, then explicitly declare the people different. | Equality can satisfy the first case; the explicit difference makes the restricted case inconsistent. | OWL does not assume every distinct name denotes a different individual. |
| Change the success definition from equivalence to subclass only. | The outcome no longer suffices to infer successful membership. | Necessary conditions alone are not a complete classification definition. |
| Use only-low records without a some-record condition. | No record existence is entailed by the universal restriction alone. | “Only” restricts possible values; “some” requires existence. |
| Test known scores 39, 40, 41 and an unknown score. | Only 39 is inferred low. | The low-score boundary is strict, and absence does not imply zero. |

### SHACL experiments

The tests remove required links, introduce two Student values, replace a typed link with an untyped identifier, use scores outside the permitted range, use wrong datatypes, duplicate contextual keys and connect records across different offerings. They also test unsupported assessment types, misplaced final outcomes, reversed dates, negative counts and missing type triples.

Each test checks that the validator reacts **as expected**. A test of an invalid score passes when the shape flags that invalid score. It does not mean that the invalid score was accepted.

Valid boundaries are also tested: scores 0 and 100 remain allowed, known negative day offsets remain allowed, and zero clicks remain allowed. Unknown scores remain warnings. This helps prevent a validator that rejects legitimate observations while catching bad ones.

## 11. What the verification establishes

| Layer | Passed checks | What was checked |
|---|---:|---|
| Core CSV/RDF pipeline | 14 | Counts, outcome answers, exact late-record identities and day differences against SQL, missing-value retention and query boundaries. |
| OWL ontology | 17 | Consistency/coherence, exact inferred identities against CSVs, vocabulary alignment, sample fidelity and reasoning semantics. |
| PostgreSQL integration | 23 per dataset | Graph equality, six SQL/RDF/virtual answer comparisons, generated SQL, SQL constraints, SHACL and committed-update freshness. |
| SHACL extension | 37 | Valid/broken behavior, value boundaries, link integrity, target coverage, sample fidelity, CSV warning identities, source fingerprints and PROV-O input/output fingerprints. |

These are counts of checks, not counts of defects or percentages of complete coverage. Several checks address related aspects of the same model. Passing the suite supports the specific properties tested.

The latest full SHACL result and its verification have matching report fingerprints when this walkthrough was prepared. The full run finished at **2026-10-15T02:51:37.486501+00:00** and the 37-check verification was recorded at **2026-10-15T02:51:53.178880+00:00** (UTC). The saved ontology report's input fingerprints also match the current ontology and data. The database counts below come from their earlier saved import checks; the Session 5 update did not recheck Neo4j or Fuseki. It did query the project PostgreSQL service through SQL and Ontop.

An appendix below lists all 37 SHACL checks from the verification file, so you can connect the summary to the exact evidence.

## 12. What Neo4j and Fuseki results mean

| Tool | Saved result | How to interpret it |
|---|---|---|
| Neo4j | 5,037 project nodes, 8,221 relationships; 815 late records. | A property-graph projection. RDF literal values become node properties, and selected types become labels. |
| Fuseki | 28,575 triples; all six available query result sets matched the local RDFLib results. | 28,470 data facts plus 105 RDFS schema triples in the default graph. Automatic RDFS inference is disabled. |
| Ontology notebook | Saved inferred class memberships, examples and explanations. | Local presentation of the reasoner evidence, with source fingerprints checked. |

The OWL inference export is separate from both database imports. It is not automatically present merely because the server contains an RDFS or OWL file.

For access, Neo4j's browser is on port **7474**, its driver/Bolt connection is on **7687**, and the configured Fuseki web service is on **3030**. The [README](../README.md) explains startup, loading and example queries. These are configured addresses, not a claim that the services are running now.

## 13. Provenance: how we know which run produced a result

There are three complementary records:

1. The [project provenance guide](project-provenance.html) explains data origins, transformations, authorship/reuse, decisions and limitations. Its JSON snapshot is a dated audit of files.
2. Each SHACL output folder contains `provenance.ttl`, recording a real validation activity with input entities, a software agent and generated report entities.

3. Each Session 5 run records the six CSVs, mapping, SQL schema, code, questions, runtime download manifest, database fingerprint and generated outputs in its own `provenance.ttl`.

The validation run uses the data, schema and shapes; it records their SHA-256 fingerprints. The validator is identified by its code fingerprint and pySHACL version. The output report fingerprints are linked back to that run. Local start/end times are recorded in UTC.

A fingerprint helps identify changed bytes. It is not a publisher signature, proof of truth or an automatically preserved history. An unchanged graph can also acquire a different file fingerprint if its Turtle serialization is reordered.

During preparation of this explanation, a newer full validation run was observed, followed by a matching new 37-check verification. It retained the same 0-violation/5-warning outcome. This illustrates why a dated provenance snapshot and the current output directory can describe different runs without their counts disagreeing. The project-wide snapshot was refreshed on 16 October, retaining the previous snapshot in docs/history/. Each integration run also has a unique output directory and its own PROV-O record.

Run `python src/validation/show_provenance.py` to inspect the latest full validation record. Copy a run's output directory before rerunning if you need to preserve its historical reports. Per-triple provenance for the entire graph and an immutable history of every earlier stage have not been implemented.

**After moving the project:** the current project folder is `D:\DESKTOP\M2\kr-oulad`, with the course folder at `D:\DESKTOP\M2\KRR`. Earlier reports may still record the old `C:` locations because those were their inputs' locations when they ran. We preserve those historical records. To produce validation reports and verification for the new location, run the complete Session 4 sequence below; it regenerates the reports with current paths. Running only the verification against old reports may fail when their recorded absolute paths no longer exist. This walkthrough checks the saved verification fingerprints against the files at their new location; the current Session 4 reports date from 15 October. Session 5 separately validates its new mapped graph in its own run directory.

## 14. How to inspect and repeat the work

For understanding, open these in order:

1. [AAA data explanation](aaa-module.md): understand the observations and their limits.
2. [Ontology results](../outputs/ontology/ontology-results.html): see what the definitions infer.
3. [Full SHACL report](../outputs/shacl/full/report.html): inspect the five actual warnings and coverage counts.
4. [Broken example report](../outputs/shacl/broken/report.html): see the Class violation caused by the changed Student link.
5. [Draft report](../outputs/shacl/draft/report.html) and [triaged sample](../outputs/shacl/sample/report.html): compare severity changes on identical facts.
6. [SHACL triage decisions](shacl-triage.md): connect each rule to its justification.

To rerun the Session 4 demonstration:

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
.\run-shacl.ps1
```

The helper expects the broken-link and naive-draft examples to return exit 1, and fails on unexpected outcomes. For the current full graph alone, use `python src/validation/validate.py`, followed by `python evaluation/verify_shacl.py` to reconcile that new run. The complete step-by-step instructions are in [README section 12](../README.md#12-session-4--shacl-validation-triage-and-gate).

This project describes historical records. It has no evaluated prediction model or natural-language interface yet. Final outcomes cannot be used as if they were known before a future prediction cutoff. The current SHACL work also does not claim completion of every separate Session 4 exercise, such as ontology version-IRI management.

## 15. A short explanation for your presentation

“We selected two offerings of OULAD module AAA and profiled their related tables. We represented the data as RDF, keeping people separate from contextual enrollments and preserving missing values. RDFS describes the vocabulary, and OWL definitions let HermiT classify records such as successful enrollments and low scores. We checked those identities against the CSVs. We then added SHACL requirements and a gate: the full graph has no blocking violations and five documented completeness warnings. Deliberately broken examples show that the gate catches faults. The README, reports and provenance records make the workflow reproducible and explain its limits.”

If asked why you did not simply remove the warnings, explain that a trustworthy graph should represent what is known and make missingness visible. A cleaner-looking report would not justify inventing marks or exam dates.

## 16. Session 5: one mapping, two ways to answer

The purpose is to show that a relational database can support our existing knowledge-graph questions in two ways. We can convert its rows to a saved graph, or query those rows through a virtual graph. PostgreSQL is the shared source; the R2RML file defines how relational keys, columns and joins become RDF identities, values and links.

```text
Six selected AAA CSVs → PostgreSQL tables and views
                                  │
                    one shared R2RML mapping
                         ┌────────┴────────┐
                         ↓                 ↓
                    Morph-KGC            Ontop
                         ↓                 ↓
                 saved RDF snapshot   SPARQL rewritten to SQL
                         ↓                 ↓
                   RDFLib + SHACL     live PostgreSQL answers
```

### What we built and why

The loader retains all columns in the six selected tables, uses composite keys for enrollments, adds foreign-key/range constraints and commits a complete load transactionally. SQL views reconstruct relationships. For example, studentAssessment supplies student and assessment IDs; joining assessments supplies the module/offering needed to link the result to the correct enrollment. A separate loader check rejects records without that enrollment. We never join only on student ID where an offering is also required.

The mapping constructs the same `https://example.org/oulad/id/` resources as the original Python conversion. Each `rr:logicalTable` selects rows; `rr:subjectMap` creates the subject; predicate-object maps emit values and relationship targets. This makes the transformation explicit and reusable by two engines. The database contains 2 offerings, 748 enrollment rows, 748 registration rows, 12 assessments, 3,149 assessment records and 413 resource rows. Its Student view deduplicates 712 student IDs.

**Materialization:** Morph-KGC reads the database and mapping, then writes 28,470 asserted triples. This is a snapshot at execution time. It can be stored, inspected or validated with the existing SHACL rules. It is different from computing new OWL class memberships.

**Virtualization:** Ontop translates each SPARQL query through the mapping into SQL and reads PostgreSQL. We retain the resulting CSV and generated SQL so you can inspect the translation. There is no need to populate a separate RDF store to execute these virtual queries. Returned answers are live relative to committed database state at query time, not a guarantee of one synchronized state across arbitrary concurrent requests.

### The questions and verified results

The full integration run **99568e1cd42b46aa8ddf05ac6d075a5b** started **2026-10-16T10:31:22.648570+00:00** and completed its checks **2026-10-16T10:33:10.438337+00:00** (UTC). All **23 checks passed**. The fixture independently passed the same 23 checks on 299 triples.

| Question file | Result rows | Comparison |
|---|---:|---|
| 01_enrollments | 2 | Same answers in all four paths |
| 02_assessments | 12 | Same answers in all four paths |
| 03_late_records | 815 | Same answers in all four paths |
| 04_low_scores | 90 | Same answers in all four paths |
| 05_outcomes | 8 | Same answers in all four paths |
| 06_unknown_scores | 3 | Same answers in all four paths |

The four paths are independent SQL, the original RDF conversion, mapped RDF and Ontop. We compare complete answer multisets, retaining duplicates while ignoring presentation order. Thus 815 means matching late-record answers, not just an equal total. The graph comparison also compares identities, predicates and typed values. Its raw-term difference is zero in this run; the comparator additionally documents equivalent RDF 1.1 string and numeric lexical forms.

Enrollment counts are grouped by offering; outcome rows are offering/outcome groups. The three unknown-score answers are preserved records whose score property is absent. Low scores and late records are historical observations, not causal explanations or predictions.

Question 2's original RDFS path is represented for Ontop by the explicit current assessment types TMA, CMA and Exam. Both versions return the same 12 assessments. No OWL ontology is passed to Ontop here; HermiT's Session 3 classifications remain a separately tested stage. Ontop's ontology support should not be equated with unrestricted OWL DL reasoning.

### How SHACL fits

The existing validator runs on the newly materialized graph plus the existing RDFS schema. It again reports **0 violations and 5 warnings**: three unknown scores and two unknown exam deadlines. The project gate passes with those visible warnings. The fixture has one unknown score and two unknown deadlines, so its warning count is three. A passing mapped graph does not prove every future virtual database state will pass: after changing source data, rematerialize and validate again.

The integration tests also attempt a duplicate enrollment key, an out-of-range score of 101, and an unknown offering. PostgreSQL rejects all three; each attempt is rolled back. SQL constraints protect the table state, while SHACL checks the graph produced by the mapping. Neither substitutes for the other.

### The change experiment, interpreted

| Stage | Low-score count | Meaning |
|---|---:|---|
| Original snapshot and virtual query | 90 | Both describe the original teaching copy. |
| Change one score to 99 and commit; query Ontop | 89 | One record no longer meets score < 40. |
| Query the old RDF snapshot | 90 | Saving a graph does not give it an automatic refresh mechanism. |
| Materialize again and query the new graph | 89 | A new snapshot reflects the committed update. |
| Restore the edited value | Original database fingerprint restored | The experiment leaves the teaching copy's data as it was. |

The experiment runs in a separate `oulad_demo` schema; the main AAA tables are unchanged. It illustrates freshness, not a general speed ranking. Query timings include local Java startup, and the source is small. The fixture performs the same experiment with counts 2 → 1. Before/after teaching artifacts remain clearly labeled and should not be mistaken for the original dataset.

### Actual implementation challenges and fixes

| Observed problem | Cause | Fix and evidence |
|---|---|---|
| Database fingerprint query failed with ORDER BY position 13 | The student_info table has 12 columns; a fixed positional sort was wrong. | Sort full rows by their JSON representation; then hash columns and rows deterministically. Both datasets now pass the load-state checks. |
| Fixture produced 300 triples rather than 299 | Morph emitted the text `None` as a decimal for a SQL NULL score. | A separate `KnownScores` mapping selects only non-NULL scores. It retains the record and its other links. Exact graph equality and unknown-score answers now pass. |
| Ontop rejected a Windows properties path as an invalid URI | Backslashes in a relative path were interpreted as URI syntax. | Pass forward-slash relative paths for mapping, properties, query and output arguments. All six virtual queries pass. |
| Lab dependencies exceed Morph's declared upper bounds | M2ENV uses newer RDFLib/PyOxigraph versions required by the course. | Install the pinned Morph package with `--no-deps`, keep the existing versions, and verify the actual mapping/query workload. CI explicitly reproduces this tested combination. |
| Need to compare changing database and saved graph meaningfully | Different source states can create a false mapping discrepancy. | Hold shared table locks during baseline comparisons; isolate intentional edits in a separate demo schema and restore the score in a finally block. |
| Need to distinguish successful checks from remote CI | Local execution does not demonstrate a GitHub runner result. | Record 23 local checks for each dataset; prepare the separate workflow and label its remote execution pending. The earlier SHACL workflow success is independently identified as user-supplied screenshot evidence. |

Failed implementation attempts retain their diagnostics in `outputs/integration/runs/`. The last-success pointers are updated only after every check and provenance verification succeeds. Known missing values remain documented limitations; no source value was invented to make the tests pass.

### How to run and inspect it

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
.\run-integration.ps1
```

Open the [integration results](../outputs/integration/integration-results.html), inspect [this run's summary](../outputs/integration/runs/99568e1cd42b46aa8ddf05ac6d075a5b/summary.json), then follow a question's CSV and generated SQL links. Read [README section 13](../README.md#13-session-5--postgresql-mappings-materialization-and-virtualization) for prerequisites, individual commands, connection settings, fixture mode and troubleshooting.

The new [integration CI workflow](../.github/workflows/integration.yml) runs the committed fixture against PostgreSQL and retains evidence artifacts. It is prepared locally; no remote execution is claimed yet. The full data and its 28,470 triples are checked locally. The [provenance guide](project-provenance.html#12-session-5-integration-provenance) records exact inputs, software, database fingerprints and both successful run IDs.

For a presentation: “We now maintain one explicit relational-to-RDF mapping. Morph-KGC uses it to save a graph; Ontop uses it to answer SPARQL directly from PostgreSQL. We compared the graph and all six questions with the original pipeline, re-ran SHACL, and demonstrated why a saved graph needs refreshing after a committed source change.”

## Appendix: all SHACL verification checks

The following table is inserted directly from the saved verification report when this guide is generated. It describes the checked behavior; it does not mean these deliberate faults occurred in the real dataset.

| # | Behavior checked | Result |
|---:|---|---|
| 1 | Real sample: 0 violations, 3 visible warnings, gate passes | Passed |
| 2 | All 12 assessment subtypes are targeted without RDFS materialization | Passed |
| 3 | Only the optional activity target is empty in the real sample | Passed |
| 4 | Broken fixture changes exactly one Student link | Passed |
| 5 | Broken Student reference blocks the gate at the expected focus node | Passed |
| 6 | Missing Student link is a SHACL minCount violation (OWL open-world contrast) | Passed |
| 7 | Two distinct Student IRIs violate maxCount without OWL identity merging | Passed |
| 8 | Score boundary -1: gate fails | Passed |
| 9 | Score boundary 0: gate passes | Passed |
| 10 | Score boundary 100: gate passes | Passed |
| 11 | Score boundary 101: gate fails | Passed |
| 12 | Zero offering length fails and its zero value is retained in the report | Passed |
| 13 | Numeric-looking string is not an xsd:decimal score | Passed |
| 14 | Removing a known score adds a warning, preserves the record and passes the gate | Passed |
| 15 | Integer banked flag is rejected after the mapping to Boolean | Passed |
| 16 | A valid Assessment from the wrong offering is caught by SHACL-SPARQL | Passed |
| 17 | Duplicate contextual enrollment key is caught across distinct nodes | Passed |
| 18 | Duplicate assessment-record key is caught across distinct nodes | Passed |
| 19 | Unexpected outcome is a vocabulary violation | Passed |
| 20 | Negative previous-attempt count is rejected | Passed |
| 21 | Negative day offsets remain permitted | Passed |
| 22 | Pass with a withdrawal date is a review warning, not a silent repair | Passed |
| 23 | Reversed dates produce a core property-pair warning | Passed |
| 24 | Outcome on Student is forbidden by maxCount zero | Passed |
| 25 | Assessment without a supported subtype is rejected | Passed |
| 26 | A record missing its type is still selected through its properties | Passed |
| 27 | Optional activity validates when present, including zero clicks | Passed |
| 28 | Negative click count is rejected | Passed |
| 29 | Activity cannot link to a resource in another offering | Passed |
| 30 | Zero-focus trap: SHACL conforms True, project gate fails | Passed |
| 31 | An empty data graph cannot pass the coverage gate | Passed |
| 32 | Saved full run matches current data, schema, shapes and validator | Passed |
| 33 | Every real sample triple is an unchanged source triple | Passed |
| 34 | Full structural focus counts match all seven CSV-derived entity counts | Passed |
| 35 | Full warning identities match the missing score/deadline CSV rows | Passed |
| 36 | Full graph gate passes with no violations and visible warnings | Passed |
| 37 | PROV-O input and output fingerprints match the actual validation run | Passed |

Evidence: [SHACL verification JSON](../outputs/shacl/verification.json), [OWL verification JSON](../outputs/ontology/verification.json), [core verification JSON](../outputs/verification.json), [dated run notes](../report/first-run.md), and [source questions and rules](questions-and-rules.md). The early run notes are chronological: statements that OWL/SHACL were future work refer to that earlier stage.
