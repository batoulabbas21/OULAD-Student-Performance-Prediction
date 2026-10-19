# Session 7: asking the OULAD graph in English

**What we added, how it works, the measured results, and what those results establish.** Updated 18 October 2026.

The new interface converts a question into SPARQL, checks the query, executes it against the existing OULAD facts and displays the returned rows. It keeps the generated query visible so you can inspect how the answer was obtained. The live experiment used **gemini-3.5-flash-lite** through the same Gemini API approach as the course lab, within the existing **M2ENV** Conda environment.

[Open the measured run report](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/report.html) · [Read the run instructions](../README.md#15-session-7--natural-language-access) · [Read project provenance](project-provenance.html#14-session-7-access-provenance)

## 1. How Session 7 connects to Sessions 1–6

| Existing work | What Session 7 uses or adds |
|---|---|
| CSV profiling | Independently calculates reference answers from the selected tables |
| RDF and RDFS | Queries 28,470 asserted facts plus 105 schema triples |
| OWL | Retains the distinction between asserted facts and separate inferred memberships |
| SHACL | Graph validation remains a separate stage; Session 7 checks generated queries |
| PostgreSQL, mappings and virtualization | The established vocabulary remains the same; this first interface executes the local RDF snapshot |
| Learning | Predictions remain in their experimental outputs; they are not presented as historical graph facts |
| Natural-language access | Adds questions → SPARQL → checked execution → answer rows and provenance |

No database service is required for this local interface. It does not connect to PostgreSQL or Ontop on every question. Session 5 remains the place to compare SQL, materialized RDF and virtual SPARQL. Refreshing the RDF snapshot changes the source fingerprint and requires a new evaluation. Fuseki's SPARQL service and this English-question server serve different purposes.

## 2. The pipeline, step by step

```text
Existing oulad.ttl + education.rdfs.ttl
        ↓ describe observed classes, properties and targets
VoID + readable schema summary
        ↓ combine rules, schema and three closest examples
Question → Gemini → candidate SPARQL
                       ↓ parse and check vocabulary
                 error → feedback → at most two repairs
                       ↓
           local read-only execution → returned rows
                       ↓
       compare with reference SPARQL and independent CSV answers
                       ↓
         readable report + response cache + run provenance
```

**VoID** is a vocabulary for describing datasets. `outputs/access/void.ttl` describes the observed graph: direct class counts, property usage and all observed target classes or datatypes. `schema.txt` makes the same information readable. This is not another ontology and does not invent data. For example, the RDFS schema declares `DailyInteraction`, but this extract contains no interaction instances; the interface explicitly marks that capability unavailable. `Assessment` is a superclass: its instances are found through subtype paths even when no record is directly typed `Assessment`.

The eight worked examples in `config/access/examples.ttl` use `sh:SPARQLExecutable`, `rdfs:comment` and `sh:select`, following the course convention. Their use of the SHACL vocabulary does **not** make them graph-validation shapes. Each example is a question paired with a query. A simple word-overlap function selects the nearest three; there is no embedding service or extra model call for retrieval.

The prompt supplies the meaning of enrollment, student, banked record, late submission, missing score and successful outcome. The user question is kept separate from these rules. Gemini receives the question, schema summary and worked queries; it does not receive entire CSV files or individual answer rows. Generated answers are executed locally; there is no second LLM call paraphrasing the rows.

## 3. What checks and repairs actually do

The repair setting parses the candidate into SPARQL algebra and checks resolved predicate/class IRIs, including aliases and full IRIs. An invented `edu:grade` is rejected because the data uses `edu:score`. It also rejects declared activity terms when the corresponding facts are absent. It supplies the failed query and diagnostic feedback to the model, for at most **three total attempts**: initial generation plus two repairs.

Every setting allows only SELECT/ASK over the local default graph and rejects remote SERVICE calls, FROM clauses, named GRAPH access and updates. Queries run in an isolated worker with a 15-second execution limit and a 10,000-row output limit. Those checks also apply when comparing the schema-only and examples settings; those two settings omit the extra vocabulary feedback loop. This is a local teaching interface, not a public service with accounts or production concurrency controls.

A valid query can still be wrong. Counting enrollments instead of distinct students is legal SPARQL with real vocabulary. Only comparison with the intended answer reveals the semantic error. The validator is an aid, not a correctness proof.

| Status | Interpretation |
|---|---|
| answered | A permitted query ran; inspect its query and returned values |
| refused | The model explicitly identified missing kinds of facts |
| invalid | Attempts were exhausted without an executable query; this is not a justified refusal |
| unsupported | Catalog mode was given a question outside its eight exact examples |
| HTTP 503 / command error | Provider, quota, request-budget or execution infrastructure failed; an incomplete evaluation must not be treated as a successful refusal |

A genuine empty result or ASK false is an answer. It is not a missing-data refusal. The HTTP contract supplies a harmless empty SELECT for refusals so the lab-style client receives syntactically valid SPARQL; the separate `status` and `reason` fields preserve the distinction.

## 4. What questions we tested

The held-out file has **10 answerable questions and 3 missing-data questions**. Its question wording is disjoint from the eight worked examples. It tests different aggregations and combinations within the same AAA vocabulary; it is not a new dataset or a statistically independent research benchmark. Some test operations are similar to the examples. The schema summary includes class counts, so some counting tasks are deliberately easy.

| Question | CSV and reference SPARQL answer |
|---|---|
| How many distinct students are represented across AAA? | 712 |
| What is the total number of enrollments in 2014J? | 365 |
| How many assessments are scheduled in AAA, including exams and tutor-marked assessments? | 12 |
| Give the number of enrollments for every final result in each presentation; show presentation, final result and count in that order. | 8 presentation/outcome groups; detailed rows in the report |
| How many non-banked assessment records were submitted strictly after their known deadline? | 815 |
| How many assessment records have a known score below 40, including banked records? | 90 |
| How many assessment records have no score recorded? | 3 |
| What is the total number of banked assessment records? | 42 |
| How many enrollments finished successfully, meaning Pass or Distinction? | 531 |
| How many scheduled assessments have an unknown deadline? | 2 |


The three correct refusal cases are personal reasons for withdrawal, instructor full names and hours spent studying online. Outcomes do not identify personal causes. Resource descriptions do not establish visits or study duration. Regions and age bands do exist, so the interface should not indiscriminately refuse every demographic question.

The oracle calculates these answers directly with pandas over `studentInfo.csv`, `studentAssessment.csv` and `assessments.csv`. It joins the assessment records to deadlines for lateness, excludes banked records in that count and checks strictly greater than the deadline. It counts missing values as missing, not zero. Before any API call, the evaluator confirms that each hand-authored reference SPARQL query agrees with its independent CSV calculation.

## 5. The measured three-setting comparison

Run **`dd0223f4396343f48a214657557b40aa`**, started **2026-10-18T12:25:42.707752+00:00**, evaluation loop finished **2026-10-18T12:28:23.320689+00:00** (UTC). Mode **record**, model **gemini-3.5-flash-lite**, **39 actual API requests** within the approved maximum of 45. The cache contains genuine provider responses for these exact prompts and model.

| Setting | Mean row F1 | Exact answers | Correct refusals | Successful repairs |
|---|---:|---:|---:|---:|
| schema | 1.000 | 10/10 | 3/3 | 0 |
| examples | 1.000 | 10/10 | 3/3 | 0 |
| repair | 1.000 | 10/10 | 3/3 | 0 |


All three settings answered all ten questions exactly and refused all three missing-data questions. Examples and repair therefore showed **no measured accuracy improvement on this benchmark**. No live repair was needed; its behavior was verified separately with deliberately faulty, scripted responses. This is a ceiling result on a small, straightforward test, not evidence that every natural-language question will work.

The report exposes every generated query, attempt, check, returned row and expected answer. It also records wrong refusals and invalid attempts. The results are one execution of one model on one small authored question set; provider output may vary on a later live run even at temperature zero. Replay repeats the recorded responses; it is not a fresh measurement of the provider.

The complete replay was also tested: [replay report](../outputs/access/runs/2d48629d7cdb4587a89ec083344283ca/report.html), run `2d48629d7cdb4587a89ec083344283ca`, with **0 API requests**. There are 26 distinct prompt/model keys for 39 live calls: examples and repair have identical initial prompts when no repair is needed. The cache retains the latest genuine reply per key; the live run's `model-calls.json` retains all 39 responses. Replay therefore verifies execution from that cache, not byte-for-byte reproduction of every repeated live generation.

## 6. How to interpret precision, recall and F1

Precision asks what fraction of returned rows are correct. Recall asks what fraction of expected rows were returned. F1 combines them: `2 × precision × recall / (precision + recall)`. The primary score preserves complete rows and duplicate multiplicity, comparing columns by projected position while tolerating renamed variables and equivalent numeric spellings. For multi-column questions the question specifies the requested column order. Both valid empty answers score 1; failed execution scores 0. ASK is scored as a boolean answer.

For a single count, such as 712 distinct students, a correct count gives F1=1 and a different count gives F1=0. For grouped outcomes, partial matching rows can give a score between 0 and 1. Mean answer F1 averages the ten answerable questions equally. Refusal correctness is reported separately over the three unanswerable questions.

The course's flattened value-set F1 is also retained for comparison. Its limitation is demonstrated by swapping presentation counts: `(2013J,383),(2014J,365)` versus `(2013J,365),(2014J,383)`. The same four isolated values appear in both answers, so the flat score is 1, but every row association is wrong, so our row-aware score is 0. Neither metric replaces reviewing whether the benchmark itself asks a useful question.

## 7. Challenges, errors and how they were addressed

| Challenge or deliberately injected error | Treatment and evidence |
|---|---|
| The lab is about Brunel logistics | Replaced domain rules, IRIs, examples, tests and oracle with OULAD meanings; never reused the Brunel response cache as an OULAD result |
| 748 enrollments versus 712 distinct students | Explicit prompt rule plus independent distinct-person test |
| Assessments use subtype classes | Included RDFS in the execution graph and used `a/rdfs:subClassOf* edu:Assessment`; reference count is 12 |
| Activity schema exists but activity data is absent | VoID describes observed facts; availability check excludes unloaded interaction vocabulary |
| Missing score/deadline could be treated as zero | Used absent-predicate queries and CSV missingness checks; counts are 3 scores and 2 deadlines |
| A model can invent a plausible predicate | Scripted `edu:grade` failure is checked and repaired to a valid score query; feedback includes the bad query |
| Repair exhaustion could look like a valid refusal | Separate invalid status; only explicit missing-data refusal counts as correct on refusal tests |
| Flat answer sets hide mismatched associations | Added the row-aware score and a swapped-count regression test |
| A query could run indefinitely or access another endpoint | Read-only algebra guard, isolated worker timeout and row bound; tested locally |
| A cache could silently provide unrelated examples | Exact model/prompt key; prompt includes data/schema fingerprints; a cache miss is an explicit error |
| Credentials could enter Git or logs | Read the existing lab key without copying it; `.env.access` is ignored; provider bodies and keys are excluded from logs |
| Model performance could be overstated | Distinguish live measurements, replay, exact catalog questions and scripted repair fault tests |

These fault injections are controlled tests, not a claim that Gemini made each mistake during the measured run. The live record above establishes which errors actually occurred. No dependency installation or Conda environment replacement was needed.

## 8. Files, evidence and viewing the result

| File or folder | Purpose |
|---|---|
| `src/access/` | Grounding, prompt/retrieval, API/cache, query execution, scoring, CLI, server and reports |
| `config/access/examples.ttl` | Eight worked example questions |
| `config/access/questions.yaml` | Ten answerable tests and three refusal tests; reference queries are not fed to the model |
| `config/access/prompt.txt` | OULAD interpretation and refusal rules |
| `evaluation/verify_access.py` | CSV reconciliation, validation, repair, scoring, timeout and HTTP tests; saved-run audit |
| `outputs/access/verification.json` | **65 passing local/evidence checks** |
| `outputs/access/llm-cache.json` | Real recorded replies, model, prompt hashes, times and reported token usage |
| `outputs/access/runs/<run-id>/` | Immutable-by-convention run folder: answers, summaries, report, manifest and PROV-O |
| `outputs/access/latest-evaluation.json` | Pointer to the latest complete evaluation |
| `outputs/access/local-results.html` | Readable local test report |
| `outputs/access/access-results.html` | Link to the most recently generated evaluation report; inspect completion status |

Open the [detailed evaluation](../outputs/access/runs/dd0223f4396343f48a214657557b40aa/report.html). For the interactive page run `python src/access/serve.py` from the project after activating M2ENV, then open **http://127.0.0.1:8007**. Default catalog mode needs no API call and supports the eight displayed examples exactly. To ask new wording, start the server with `--mode record --env-file D:\DESKTOP\M2\KRR\demos\.env`. Each live user question can consume up to three requests; the default server lifetime budget is 45 requests. Ctrl+C stops it.

This work adds a local verification suite; it does not add or claim a new GitHub Actions run. Existing SHACL and integration CI keep their previous scope. Run the local tests before committing. Raw data are still ignored by Git, so a fresh clone must recreate the selected RDF before running Session 7. The README lists every command.

## 9. Sources and course relationship

The implementation adapts the local course's `demos/session-07-access-layer`: `access_layer.py`, `make_void.py`, `evaluate.py`, `score_utils.py`, `serve.py`, examples and question-set pattern. OULAD domain rules, independent CSV oracle, process limits, row scoring, interface and provenance were written for this project; the original lab files were not changed.

- [W3C VoID guide](https://www.w3.org/TR/void/) explains dataset class/property partitions and statistics.
- [Google's Gemini compatibility documentation](https://ai.google.dev/gemini-api/docs/openai) describes the chat-completions endpoint used by the lab and this project.
- [PyOxigraph store documentation](https://pyoxigraph.readthedocs.io/en/stable/store.html) documents the local SPARQL engine.

The tested environment retained Python 3.12.15; package versions for this run are rdflib 7.6.0, pyoxigraph 0.5.11, requests 2.34.2, pandas 2.3.3, PyYAML 6.0.3. The inventory records the tested installation; it is not a complete dependency lockfile.
