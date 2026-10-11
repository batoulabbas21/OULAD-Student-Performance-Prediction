# Read the tables before building triples

The official field definitions are at https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/.
The profile shows the actual CSV names and types. In particular, the course duration column in the
file is module_presentation_length, though the prose dictionary abbreviates its name to length.

| File | Grain (one row means...) | Important columns | Join |
|---|---|---|---|
| courses.csv | One module offering | code_module, code_presentation, module_presentation_length | Composite offering key |
| studentInfo.csv | One enrollment | id_student, offering key, final_result, num_of_prev_attempts | Offering key -> courses |
| studentRegistration.csv | Registration information for one enrollment | Enrollment key, date_registration, date_unregistration | Full enrollment key -> studentInfo |
| assessments.csv | One assessment | id_assessment, offering key, assessment_type, date, weight | Offering key -> courses |
| studentAssessment.csv | One recorded student-assessment result | id_student, id_assessment, date_submitted, is_banked, score | Assessment -> assessments -> offering; student + offering -> enrollment |
| vle.csv | One resource within an offering | id_site, offering key, activity_type, week_from, week_to | Offering key -> courses |
| studentVle.csv | Daily clicks on a resource by an enrolled student | Enrollment key, id_site, date, sum_click | Full enrollment key and resource key |

Never join studentAssessment to studentInfo on student ID alone: repeated enrollments could multiply records.
First recover its offering through assessments, then join using student ID + offering.

## What is represented in this first graph

- Modules, offerings, students, enrollments, assessment subtypes, assessment records, and resources.
- Final result, previous attempts, age band, region, and entry education on enrollments.
- Registration and withdrawal day offsets, optional recorded scores and deadlines.
- Optional daily interactions with click totals when --activity is selected.

Some raw attributes, such as disability, deprivation band, and gender, are deliberately not mapped
in the first graph because the initial questions do not require them. They remain in the original
tables and in the descriptive profile. Additional ontology properties should be justified by questions.

## Meaning of missing and unusual values

- The downloaded UCI files use `?` in several columns. The loader treats this as missing, alongside empty cells.
- A negative day means an event before the offering start; it is not automatically erroneous.
- Missing score is unknown, not zero. A present zero remains a real typed numeric literal.
- A banked record is a result carried from an earlier presentation; do not treat its submission timing as a new submission.
- Exact missing deadlines are not manufactured from approximate course-end descriptions.
- Click totals count recorded interactions, not hours or comprehension.
- B and J offerings can have different structures; avoid treating their day schedules as interchangeable.

## Three categories to write in your report

1. Documented source definitions (e.g. day offsets, score range).
2. Checks confirmed on this release/subset (e.g. key uniqueness).
3. Project policies (e.g. 28-day window, warning treatment, namespace).

Record the scope with every count: raw core tables, selected module, or optional activity extension.
