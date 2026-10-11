# What exactly is module AAA?

AAA is an anonymized module identifier in OULAD. The dataset paper classifies it as **Social Sciences**.
Its actual course title, syllabus, instructor identities, and assignment content are not revealed.
Do not expand AAA into an invented acronym or call it a specific subject such as psychology.
At the Open University, a module is a course; a presentation is one offering of that course.

Source for domain and naming conventions: Kuzilek, Hlosta, Zdrahal (2017),
https://pmc.ncbi.nlm.nih.gov/articles/PMC5704676/ (Table 1 and Background).
The remaining counts below were computed from this project's downloaded CSVs.

## One module, two offerings

| Field | AAA / 2013J | AAA / 2014J |
|---|---:|---:|
| Start month encoded by presentation | October 2013 | October 2014 |
| Recorded offering length | 268 days | 269 days |
| Enrollment rows | 383 | 365 |
| Assessment definitions | 6 | 6 |
| Tutor-marked assessments (TMA) | 5 | 5 |
| Final exam definitions | 1 | 1 |
| Resource descriptions | 211 | 202 |
| Final outcome: Pass | 258 | 229 |
| Final outcome: Distinction | 20 | 24 |
| Final outcome: Fail | 45 | 46 |
| Final outcome: Withdrawn | 60 | 66 |

J is the presentation code for October, not January or June. The CSVs do not supply an exact
calendar starting day; preserve relative day offsets rather than inventing one.

There are **748 enrollment rows but 712 distinct student IDs**. Exactly 36 IDs occur in both
AAA offerings. Therefore a Student must be different from an Enrollment in our graph.
Do not attach a single finalResult directly to Student: a repeated student can have one outcome
for 2013J and another for 2014J.

## How assessment is organized

Both offerings have the same recorded TMA schedule and weights:

| Assessment position | 2013J ID | 2014J ID | Deadline (days after offering start) | Recorded weight |
|---|---|---|---:|---:|
| TMA 1 | 1752 | 1758 | 19 | 10% |
| TMA 2 | 1753 | 1759 | 54 | 20% |
| TMA 3 | 1754 | 1760 | 117 | 20% |
| TMA 4 | 1755 | 1761 | 166 | 20% |
| TMA 5 | 1756 | 1762 | 215 | 30% |
| Exam | 1757 | 1763 | Unknown exact day | 100% |

The five TMA weights sum to 100%; the exam separately has weight 100. Do not sum these into
a supposed 200% final grade or assume an undocumented formula combining them.
The current extract supplies no studentAssessment rows for the two AAA exam IDs, although
the exam definitions exist. Missing exam records are not evidence of zero marks or nonattendance.

There are 3,149 assessment-result records across AAA. Of these, 42 are banked results
carried from an earlier offering and 3 have no score. A banked record is not necessarily a new
submission in the current offering, which is why our late-submission query excludes it.

## Why this is a useful first project

AAA provides a small, understandable connected dataset. It is enough to practice identities,
relationships, unknown values, SPARQL, and the distinction between RDFS inference and validation.
It also provides a natural chronological example: a 2013 offering and a later 2014 offering.

This is a teaching choice, not a claim that AAA represents every course or is an ideal final
machine-learning benchmark. For later learning, account for the 36 repeated students and use
only features available at the prediction cutoff. The historical graph contains final outcomes.

## Read the graph as a story

```text
Module AAA
  -> CourseOffering AAA/2013J
     -> Enrollment of student X in that offering
        -> AssessmentRecord for one of that offering's assessments
  -> CourseOffering AAA/2014J
     -> A separate Enrollment if student X appears again
```

The actual relationship directions are defined in ontology/education.rdfs.ttl. For example,
Enrollment --inOffering--> CourseOffering --offeringOf--> Module.

## Questions that now have precise meanings

- "How many students took AAA?" Specify unique IDs (712) or enrollment rows (748).
- "Which year had more enrollments?" 2013J: 383 versus 365 in 2014J.
- "Which submissions were late?" Non-banked records with both dates known and submission day > deadline.
- "Did a low TMA score mean the student failed AAA?" Compare the assessment record with that enrollment's separately recorded outcome.
- "What did AAA teach?" The broad domain is Social Sciences; detailed teaching content is not available.
- "How many hours did students study?" The activity data records clicks, not study duration.

The core graph includes resource descriptions but not daily interactions. Enable --activity and
rebuild the graph before answering who accessed which resource.
