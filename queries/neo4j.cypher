// Run one block at a time in Neo4j Browser. Switch results to Graph for paths.
// Every query selects the currently verified OULAD snapshot.

// 1. Students, enrollments, and course offerings (small visual neighborhood).
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(s:OULAD:Student)<-[:HAS_STUDENT]-(e:OULAD:Enrollment)-[:IN_OFFERING]->(o:OULAD:CourseOffering)
WHERE e.snapshot=m.activeSnapshot
RETURN p LIMIT 30;

// 2. Module, offerings, and assessment definitions.
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(a:OULAD:Assessment)-[:ASSESSMENT_IN_OFFERING]->(o:OULAD:CourseOffering)-[:OFFERING_OF]->(module:OULAD:Module)
WHERE a.snapshot=m.activeSnapshot
RETURN p;

// 3. Show recorded late submissions; a missing deadline does not qualify.
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(e:OULAD:Enrollment)<-[:RECORD_FOR_ENROLLMENT]-(r:OULAD:AssessmentRecord)-[:FOR_ASSESSMENT]->(a:OULAD:Assessment)
WHERE r.snapshot=m.activeSnapshot AND r.isBanked=false AND r.submissionDay>a.deadlineDay
RETURN p LIMIT 25;

// 4. Low-score records as a graph.
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(e:OULAD:Enrollment)<-[:RECORD_FOR_ENROLLMENT]-(r:OULAD:AssessmentRecord)-[:FOR_ASSESSMENT]->(a:OULAD:Assessment)
WHERE r.snapshot=m.activeSnapshot AND r.score<40
RETURN p LIMIT 25;

// 5. Outcomes per offering (Table result).
MATCH (m:OULADProject {name:'oulad'})
MATCH (e:OULAD:Enrollment)-[:IN_OFFERING]->(o:OULAD:CourseOffering)
WHERE e.snapshot=m.activeSnapshot
RETURN o.name AS offering,e.finalResult AS outcome,count(e) AS enrollments
ORDER BY offering,outcome;

// 6. Resource metadata is available even before daily activity is loaded.
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(r:OULAD:LearningResource)-[:RESOURCE_IN_OFFERING]->(o:OULAD:CourseOffering)
WHERE r.snapshot=m.activeSnapshot
RETURN p LIMIT 30;

// 7. Optional: requires rebuilding RDF and reloading Neo4j with --activity selected.
MATCH (m:OULADProject {name:'oulad'})
MATCH p=(e:OULAD:Enrollment)<-[:INTERACTION_FOR_ENROLLMENT]-(i:OULAD:DailyInteraction)-[:WITH_RESOURCE]->(r:OULAD:LearningResource)
WHERE i.snapshot=m.activeSnapshot AND i.interactionDay>=0 AND i.interactionDay<28
RETURN p LIMIT 30;
