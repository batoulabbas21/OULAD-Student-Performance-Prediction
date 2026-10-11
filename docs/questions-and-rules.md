# OULAD: questions, follow-up questions, and rules

## Project boundary

We describe observed enrollment, assessment, and resource activity for selected course offerings.
The first version uses module AAA across its available offerings. It answers historical questions.
It does not predict outcomes yet, diagnose students, or explain causes of failure.
The labels AAA and presentation codes are anonymized identifiers: do not invent module titles.

## A question should lead to a relationship, a check, and an answer

| ID | Initial competency question | Follow-up question | What we need | Current implementation |
| --- | --- | --- | --- | --- |
| Q1 | How many enrollments are in each offering? | How many distinct students? Does a student occur in multiple offerings? | Enrollment -> Student and CourseOffering | queries/01_enrollments.rq answers counts; cross-offering list is an extension |
| Q2 | Which assessments belong to an offering? | What types, deadlines, and weights do they have? Which deadlines are unknown? | Assessment -> CourseOffering, assessment subtype, optional deadline | queries/02_assessments.rq |
| Q3 | Which recorded submissions were after the deadline? | How late? Which enrollments recur? Do they have different outcome distributions? | AssessmentRecord -> Assessment and Enrollment, banked flag, relative days | queries/03_late_records.rq answers the list and days late; aggregations are extensions |
| Q4 | Which recorded scores are below 40? | Are they banked? Does low assessment performance always accompany a final Fail? | AssessmentRecord score, banked flag, enrollment final result | queries/04_low_scores.rq; outcome comparison is an extension |
| Q5 | What final outcomes occur in each offering? | What is the success proportion, and what denominator did we choose? | Enrollment final result and offering | queries/05_outcomes.rq; success proportion defined below |
| Q6 | Which assessment records have no score? | Is missingness concentrated in one assessment type? Are exam records incomplete? | Record existence separately from score existence | queries/06_unknown_scores.rq; type comparison is an extension |
| Q7 | What resources are available? | Which activity types occur? | LearningResource -> CourseOffering, activity type | RDF includes resource metadata; additional query is a student exercise |
| Q8 | Which enrollments have recorded clicks in days 0-27? | How many resources? How do the distributions differ by final outcome? | DailyInteraction -> Enrollment and LearningResource | queries/07_early_activity.rq, only with --activity |
| Q9 | When did students register or withdraw? | How many registered before day zero? Are status and withdrawal date consistent? | Enrollment registrationDay and unregistrationDay | Profiling checks date/status consistency; timeline query is an extension |
| Q10 | What general assessment types can RDFS infer? | Why did a subject become an Enrollment after a hasStudent assertion? | RDFS subclass, domain, range | python src/graph/rdfs_entailment_demo.py |

Follow-up questions are a roadmap; do not claim every extension is already implemented.
Associations in Q3, Q4, and Q8 do not establish causation. Final outcomes describe enrollments, not a permanent student trait.

## Operational definitions (project decisions)

1. **Recorded late submission:** is_banked = 0, known submission day and known deadline,
   submission day > deadline day. A same-day submission is not late under this definition.
   This describes the recorded deadline, not proof of misconduct or the absence of extensions.
2. **Low assessment score:** a present score < 40. This matches the source assessment threshold;
   it does not imply the student's entire module was failed.
3. **Successful enrollment:** final_result in {Pass, Distinction}. If reporting its proportion,
   default denominator is all enrollments in that offering, including Fail and Withdrawn;
   present a separate completion-only rate if needed and name its denominator.
4. **Early activity window:** 0 <= interaction day < 28. This is our chosen 28-day window.
   Pre-start activity is preserved but excluded from this particular statistic.
5. **Missing fact:** no value asserted. Missing score is not zero; no loaded interaction is
   not evidence that the person did not study offline.

## Source constraints and candidate checks

| Rule | Status | Action now / later |
| --- | --- | --- |
| Every course offering has a module and presentation code | Structural key | Check null and duplicate composite keys; later SHACL cardinality |
| An enrollment is identified by student + module + presentation | Project identifier aligned with source table grain | Do not use student ID alone as the enrollment key |
| Assessment ID identifies an assessment | Candidate key verified on the loaded data | Fail the build on nulls or duplicates |
| A recorded student-assessment pair identifies an AssessmentRecord in this release | Candidate key, checked rather than blindly assumed | Fail on duplicates; review rather than silently collapse |
| Child references must resolve to the right offering, enrollment, assessment, and resource | Referential integrity | Check full keys, not just student or resource ID |
| A present score lies in [0,100] | Documented source range | Error on violation; missing score is a warning |
| Assessment type is TMA, CMA, or Exam | Documented vocabulary | Error on unknown values |
| Banked flag is 0 or 1 | Source flag encoding | Store as xsd:boolean; avoid treating banked records as fresh submissions |
| Final result is Pass, Distinction, Fail, or Withdrawn | Expected file vocabulary | Error on unexpected labels; record observed values in profiling |
| Date offsets are integers when present | Source representation | Preserve signed day offsets; never parse them as calendar dates |
| Click counts and previous attempts are nonnegative integers | Count semantics | Check ranges and integrality |
| Offering length is a positive integer | Duration semantics | Error on invalid values |
| Assessment weights individually lie in [0,100] when present | Percentage semantics | Check per row; do not require all exams + assignments to sum to 100 |
| Registration precedes withdrawal when both are known | Candidate consistency rule | Review warning; do not silently repair |
| Withdrawn outcome agrees with recorded unregistration | Documented intended relationship | Review disagreement and missingness; do not synthesize dates |
| Planned resource start week does not exceed end week | Candidate consistency rule | Review if both values are present |

These Python checks are the first validation layer. SHACL comes later. The current graph builder
blocks recorded errors and preserves optional missing values. A warning can still require a modeling decision.

## Rules we must NOT assert

- Every date must be nonnegative: students can register before the offering starts.
- Every student must have an exam score: the source notes that some exam results are not stored.
- Every assessment must have an exact known deadline: missing exam dates need documented treatment.
- All assessment weights, including exams, must total 100: exams are commonly weighted separately.
- Every student has exactly one module or outcome: enrollments provide the context.
- A low assessment score logically implies final Fail: final_result is separately observed.
- More clicks cause success: counts do not establish causality or time spent studying.
- No recorded submission implies zero: absence and an observed numeric zero are different facts.

## Refusals and boundaries

| Question | Appropriate response |
| --- | --- |
| Why did this student withdraw? | The data records an outcome/date, not the personal cause. |
| Who taught AAA? | Instructor identities are outside this dataset. |
| What is the student's exact age or name? | These are not supplied; age bands are not exact ages. |
| How many hours did this student study? | Click totals are not durations. |
| Will this student fail? | This historical RDF/RDFS phase does not yet contain an evaluated prediction model. |
| Which resources did the student access? (core build) | Activity was not loaded; load the activity extension before answering. |

## Defense questions for you

1. Why do Student, Module, CourseOffering, and Enrollment need different identifiers?
2. Why put age band/region/final result on Enrollment rather than making them timeless Student facts?
3. Why retain an AssessmentRecord even when its score is unknown?
4. Why exclude banked records from the late-submission query?
5. What is a known zero, an absent triple, and a query returning no rows?
6. Why does rdfs:domain infer a type rather than reject the subject?
7. Why can't RDFS enforce a score range or exactly one student per enrollment?
8. How did you check that converting rows to RDF did not lose records or change answers?
9. Which assumptions are source definitions, observed regularities, or your own policies?
10. What would leak if final outcomes or post-cutoff activity entered the future learning graph?

## Sources

- Official data dictionary: https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/
- UCI archive and license: https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset
- Kuzilek, Hlosta, Zdrahal (2017): https://doi.org/10.1038/sdata.2017.171
- RDFS specification: https://www.w3.org/TR/rdf-schema/

Source pages describe the data. The questions, IRIs, schema, warnings policy, and first module selection are project design choices.

