# Modeling decisions

1. Start with AAA across available offerings; expand after the small graph passes checks.
2. Keep raw CSVs unchanged and store a download manifest.
3. Model Student, Module, CourseOffering, and Enrollment separately.
4. Store final outcome and contextual student attributes on Enrollment.
5. Name studentAssessment entities AssessmentRecord because banked results are not necessarily fresh submissions.
6. Use signed integer day offsets, not fabricated calendar dates.
7. Missing optional values produce absent triples, not zeros, false flags, or "nan" strings.
8. Unknown exam deadlines remain unknown; the source's approximate end-of-week description is not an exact date.
9. Late-record query excludes banked results and requires both recorded dates.
10. RDFS entailment is distinct from validation. Python checks precede conversion; Session 4 SHACL validates the asserted RDF afterward. Violations and empty required targets block the gate; documented warnings remain visible.
11. The lightweight profile checks relationships. Optional ydata HTML follows the Session 1 lab pattern.
12. Daily activity is optional. A core build marks its activity question unavailable in status.json.
13. Generated reports reflect their recorded scope; no all-university or causal claims follow from one module.

## Add your observations after opening the reports

- Which values are missing, and what does each missingness pattern mean?
- Which candidate keys and foreign keys passed or failed?
- Which warnings require changes to the model or queries?
- Which question justified each class and property?
- What does the subset omit?

## Session 6 learning decisions

- Use Enrollment as the classification unit and Fail/Withdrawn as the positive outcome.
- Use day 60 as a fixed teaching cutoff, exclude known prior withdrawals, and split 2013J → 2014J.
- Purge earlier enrollments for students present in the future offering; report the prevalence change.
- Whitelist early nonbanked submission observations; exclude scores without publication timestamps and all outcome-derived inputs.
- Fit imputation, constant-column filtering and scaling only on training data.
- Compare GraphSAGE with both simple counts and logistic regression; report all three seeds.
- Treat TransE as historical link reconstruction, with identical candidate sets and train-only popularity counts.
- Report unfiltered and filtered ranks with candidate-set sizes and random-rank references.
- Keep predictions separate from asserted facts; do not treat scores as calibrated probabilities or causal explanations.
