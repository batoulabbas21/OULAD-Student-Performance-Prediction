# RDFS demonstration

This is a bounded sample, not the full inferred dataset.

Before: 121 triples. After: 265 triples.

Specific assessment types entail Assessment; Student entails Person.

- https://example.org/oulad/id/assessment/1752 is inferred to be an Assessment.
- https://example.org/oulad/id/assessment/1753 is inferred to be an Assessment.
- https://example.org/oulad/id/assessment/1754 is inferred to be an Assessment.

Domain demonstration: asserting demo:not-a-real-enrollment hasStudent a student
infers that the subject is an Enrollment. RDFS raises no validation error.
Range similarly infers the type of the object; it does not check a dropdown list.
Required fields, uniqueness, score ranges, and cross-record consistency need explicit checks/SHACL.