# Small real-data integration fixture

These six CSVs are a connected subset of the project's OULAD AAA extract.
`selection.json` records their selection, source fingerprints and row counts.
`expected.ttl` is the corresponding 299-triple reference graph, derived from
the existing Session 4 real-data fixture. It retains one unknown score and
two unknown assessment deadlines; these produce three SHACL warnings.

Source: Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2015), *Open University Learning
Analytics dataset*, UCI, https://doi.org/10.24432/C5KK69.
License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/.
Modification: relational selection for a small reproducible teaching/CI example;
unknown values remain empty. These data are historical and anonymized.

Run from the project root with PostgreSQL and Ontop prepared:

```powershell
python evaluation/verify_integration.py --fixture
```

This uses `oulad_fixture` and `oulad_fixture_demo` by default, separate from
the complete AAA tables. The demo temporarily edits one score and restores it.
The fixture is not a substitute for validating the complete AAA graph locally.
