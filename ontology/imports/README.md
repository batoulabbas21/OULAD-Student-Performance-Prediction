# Published vocabulary reuse

The cached `foaf.rdf` is the original RDF/XML downloaded from
https://xmlns.com/foaf/spec/index.rdf on 2026-10-12.
Its SHA-256 is `3d859b5d92a2c3d041545d014fa826f682ca06d056af8c7b31e32d930abf2bc5`.

FOAF Vocabulary Specification 0.99 is by **Dan Brickley and Libby Miller**,
copyright 2000-2014. The specification states that its documentation and accompanying RDF
are licensed under [Creative Commons Attribution 1.0](https://creativecommons.org/licenses/by/1.0/).
Source and attribution: [official FOAF specification](https://xmlns.com/foaf/spec/).

`prepare_ontology.py` creates a deliberately selected fragment in the generated workspace:

- OWL class declarations for `foaf:Person` and `foaf:Agent`.
- Their source labels and comments.
- The source axiom `foaf:Person rdfs:subClassOf foaf:Agent`.
- A new project ontology header documenting this selection.

The project keeps the original FOAF entity IRIs. Its own `edu:Person` is a subclass of
`foaf:Person`; it is not declared equivalent to every FOAF person. No personal names or
additional personal attributes are invented.

This is **not a complete FOAF import**, and not a claim that the fragment preserves every
FOAF entailment. Other FOAF terms, equivalences, disjointness and property axioms are omitted.
The full snapshot remains unchanged for inspection. Loading the complete vocabulary through
Owlready2 raised a property-kind warning for `foaf:name`; the deliberately small fragment
avoids using those unrelated property axioms. The delivered reasoner results apply to the
documented fragment and project ontology.

This adapts the Session 3 reuse lesson to people in education. The lab's supply-chain imports
are not meaningful parents for OULAD's enrollments or assessment records. A BFO alignment would
require a further modeling decision about persons, roles, participation processes and records;
this starter does not claim to provide that alignment.
