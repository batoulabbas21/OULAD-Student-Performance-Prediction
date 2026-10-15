# SHACL rules and triage decisions

Session 4 extension, 14 October 2026. The shapes are in [oulad-shapes.ttl](../shapes/oulad-shapes.ttl). The runnable steps are in [README section 12](../README.md#12-session-4--shacl-validation-triage-and-gate).

## What is being validated?

The validator loads the asserted OULAD data and the RDFS schema into a temporary graph. It does **not** load the OWL ontology, inferred types or synthetic ontology-error examples. It does not modify the source graph. Class targets and `sh:class` recognize the declared subclass hierarchy: a TutorMarkedAssessment counts as an Assessment without materializing its superclass type.

Automatic domain/range inference is disabled. Otherwise, a faulty link could cause an untyped target to acquire the very class that a shape should be checking. Property-based targets additionally find records whose type triple was accidentally removed.

## Rule coverage

| Requirement | SHACL treatment | Severity / boundary |
|---|---|---|
| Student identifier | One digit-only string; uniqueness across nodes | Violation |
| Offering module, presentation and length | One typed Module link; one presentation code; positive integer length; unique module/code pair | Violation |
| Enrollment context | Exactly one typed Student and CourseOffering; unique student/offering pair | Violation |
| Final result vocabulary | Exactly one of Pass, Distinction, Fail, Withdrawn | Violation |
| Outcome belongs to enrollment | `sh:maxCount 0` for finalResult on Student | Violation; project modeling policy |
| Previous attempts | At most one value; nonnegative integer when present | Violation |
| Assessment type | Exactly one supported TMA/CMA/Exam subtype via `sh:xone` | Violation |
| Assessment belongs to an offering | One typed CourseOffering link | Violation |
| Known assessment weight | At most one decimal in [0,100] | Violation; no combined weight-sum constraint |
| Record links and key | One typed Enrollment and Assessment; unique enrollment/assessment pair | Violation |
| Known score | At most one decimal in [0,100] | Violation |
| Banked flag | Exactly one Boolean | Violation; CSV 0/1 has already been mapped |
| Known day offsets | At most one integer value; negative offsets are allowed | Violation for incorrect datatype/multiplicity |
| Unknown score or deadline | Separate `sh:minCount 1` completeness shapes | Warning; no fabricated values |
| Unknown submission or registration day | Completeness checks | Warning |
| Registration after withdrawal | Core `sh:lessThanOrEquals` comparison on the same enrollment | Warning |
| Outcome versus withdrawal date | SHACL-SPARQL checks missing/unexpected date presence | Warning |
| Record offering consistency | Compare enrollment's offering with assessment's offering | Violation; SHACL-SPARQL across linked nodes |
| Resource structure | One typed offering and a nonempty activity type | Violation |
| Optional daily activity | Typed enrollment/resource links, integer day, nonnegative integer clicks, matching offerings | Violation when activity is present; empty activity target is permitted |

Core constraints express cardinality, datatype, ranges, vocabulary, subtype alternatives, forbidden properties and the same-node date comparison. SPARQL handles uniqueness across distinct nodes, comparisons along different relationship paths, and conditional withdrawal-date review.

The source rule list also contains **studied credits** and **resource start/end weeks**. These fields are not mapped into the current RDF, so their checks remain in Python profiling. SHACL cannot validate values that were never mapped. Assessment/resource IDs are encoded in IRIs; source key checks remain necessary because duplicate rows may already have collapsed to one RDF node or triple.

## Triage: why five warnings remain

| Source issue | Focus node suffix | Decision |
|---|---|---|
| Missing score | `assessment-record/260355/1754` | Keep the record, omit the unknown score and review completeness |
| Missing score | `assessment-record/2606802/1760` | Same decision |
| Missing score | `assessment-record/721259/1752` | Same decision |
| Missing exam deadline | `assessment/1757` | Keep the exam and leave its exact date unknown |
| Missing exam deadline | `assessment/1763` | Same decision |

These are the five results in the current full-graph report. They match the missing-value identities in the selected CSVs. They are completeness limitations, not evidence of a malformed numeric value. A present score of 101, an incorrect datatype or a broken relationship remains a blocking violation.

The generated first draft changes only score/deadline presence severity to Violation. Running it on the small sample produces **3 violations**. The triaged shapes report the **same three facts as warnings**. No row is deleted and no missingness result is hidden. The full graph has five warnings because it contains two additional unknown-score records outside the small sample.

Late submissions and low scores are valid observations. They answer analytical questions and do not automatically make a graph invalid. This project does not turn every undesirable outcome into a validation error.

## Reading a report

- **Focus node:** the record being checked.
- **Path:** the property involved, for example `edu:score`.
- **Constraint:** the failed requirement, such as `MinCountConstraintComponent`.
- **Severity:** whether the issue blocks the project gate or stays in the review queue.
- **Message:** the project's explanation and recommended interpretation.

Open the [full HTML report](../outputs/shacl/full/report.html). Its JSON, CSV and standard SHACL Turtle companions preserve the detailed evidence.

With strict pySHACL settings, any result, including a warning, means `conforms=False`. The **project gate** is a separate policy: pass only when there are no violations, no unknown severities and no empty required targets. It permits warnings and displays them. Exit code 0 means gate pass, 1 means gate failure, and 2 means an execution error.

The 14 target-bearing shapes are counted before validation. Thirteen should have nodes in the current core build; only the optional DailyInteraction shape may be empty. Nonzero coverage is useful protection, but does not prove completeness by itself. Full verification additionally compares seven entity counts with the CSVs.

## Fault examples and reproducibility

The supplied valid fixture contains **299 unchanged triples** from the real AAA graph: seven enrollments, their assessment records, all 12 assessments, one resource from each offering and the required linked entities. Its selection record contains the source fingerprint and selected identifiers.

`broken.ttl` changes exactly one Student link on enrollment `AAA/2013J/100893` to an untyped teaching identifier. It should produce one Class violation while retaining the same three completeness warnings. Other boundary and fault tests are constructed only in memory. They never overwrite the real RDF or enter Neo4j/Fuseki.

Every validation run writes input and validator fingerprints, tool versions, timestamps, target counts and a unique run ID. Its `provenance.ttl` links the data/schema/shapes used by a real validation activity to the generated reports. The reports in an output directory are replaced on rerun; copy that directory if an earlier run must be preserved.

The GitHub workflow validates the committed fixture and checks deliberate faults. It does not download the ignored full dataset. It has been prepared locally; enabling a required check for merging needs repository branch protection after the workflow has been pushed.

Sources: [local Session 4 lab](../../KRR/demos/session-04-shacl/README.md), [W3C SHACL specification](https://www.w3.org/TR/shacl/), and [pySHACL documentation](https://github.com/RDFLib/pySHACL).
