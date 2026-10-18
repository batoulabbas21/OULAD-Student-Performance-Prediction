# Session 6 results explained

Updated **18 October 2026**. This chapter reports the actual run `f7649738f7414536bc2395ef7496eebf`. Its start and finish timestamps are **2026-10-17T21:32:30.408391+00:00** and **2026-10-17T21:33:16.413705+00:00** (UTC). It passed **21 learning checks** and **54 independently recomputed evidence checks**.

### The result first

For predicting eventual Fail/Withdrawn outcomes in the future offering, **logistic regression has the highest average precision among the tested valid models**: 0.526, compared with GraphSAGE's three-seed mean 0.502, the submission-count baseline 0.444, and the constant-score reference 0.256. This is a measured comparison on one cohort; no statistical claim of universal superiority follows.

For reconstructing hidden historical submission links, **the popularity-count baseline beats TransE in every seed**, both with and without filtering. A more complex method does not automatically help. That is a useful Session 6 finding, not an experiment to hide or tune away.

Open the [learning results report](../outputs/learning/learning-results.html) for charts and downloadable results. The [full run summary](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/summary.json) contains every seed, split, model setting and count.

### 1. What does “initial count” mean here?

The original facts and the test population must have separate denominators:

| Population or stage | Enrollments | Successful: Pass/Distinction | Unsuccessful: Fail/Withdrawn |
|---|---:|---:|---:|
| Original AAA data | 748 | 531 | 217 |
| Original 2013J | 383 | 278 | 105 |
| Original 2014J | 365 | 253 | 112 |
| Eligible at day 60, both offerings | 701 | 531 | 170 |
| Eligible 2013J before student separation | 361 | 278 | 83 |
| Final training cohort, 2013J | 335 | 278 | 57 |
| Final test cohort, 2014J | 340 | 253 | 87 |

There are 47 withdrawals already recorded by day 60: 22 in 2013J and 25 in 2014J. They are excluded because predicting a withdrawal already known at the prediction time would be misleading. Everyone in this extract registered by the cutoff; the eligibility rule also handles not-yet-registered records. A withdrawal after day 60 is retained as a future outcome, while its date is excluded from the features.

There are 36 students in both original offerings. Of their 2013J enrollments, ten were already excluded by the cutoff rule and 26 remained eligible. We remove those 26 from training so no test student appears in training. All 26 had unsuccessful earlier outcomes. Consequently the training positive share falls to **17.0%**, whereas the test share is **25.6%**. This selection/prevalence difference is a real limitation, not something to conceal.

The models' predicted counts must therefore be compared with **87 unsuccessful outcomes out of 340 test enrollments**, not with all 217 historical unsuccessful enrollments. No model result changes the original 531/217 facts.

### 2. The two learning questions

**Node classification:** at day 60, among enrollments still registered, can early recorded behavior help rank eventual unsuccessful outcomes? The node is Enrollment, not Student: the outcome belongs to participation in one offering. The positive label 1 combines Fail and Withdrawn; label 0 combines Pass and Distinction. This does not distinguish causes or types of unsuccessful outcome.

**Link prediction:** after hiding some observed enrollment-to-assessment submission links, can the model rank the hidden true assessment? This uses historical nonbanked records across both offerings. It is a separate graph-completion benchmark, not a forecast of future participation and not an assessment recommendation system.

### 3. From RDF to safe model inputs

The runner reads the successful Session 5 materialized RDF, currently `outputs/integration/runs/7c0b60e5ae2b4e7da058f851b1c8286c/oulad-mapped.nt`. It checks its receipt and the selected CSV fingerprints before using it. If no integration result exists, it explicitly falls back to the original `data/processed/oulad.ttl`. The current run used the mapped graph. No live PostgreSQL, Neo4j or Fuseki service is needed during learning.

The classification builder permits only five candidate enrollment features:

| Feature | Meaning at day 60 |
|---|---|
| previous_attempts | Recorded number of previous attempts; later removed because it is constant in training. |
| registration_day | Signed day relative to the offering start; negative values remain meaningful. |
| early_submission_count | Number of nonbanked records with a known submission date on or before day 60. |
| early_late_count | Among those records, how many were after a known scheduled deadline. |
| last_submission_day | Latest recorded submission day in that permitted window; absent if no such record exists. |

Scores are deliberately excluded: the release gives submission dates, but no grade-publication timestamp proving which grades were available by day 60. Final outcomes, post-cutoff records, withdrawal dates, and OWL-derived SuccessfulEnrollment/WithdrawnEnrollment classes are also excluded. IDs locate rows and edges but are not numerical predictors or identity embeddings. Demographic fields and daily click activity are not used by this model.

The [learning RDF](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/graph/learning-input.ttl) contains the permitted enrollment features and early-submission links, with assessment type, scheduled deadline and weight on neighboring assessment nodes. Labels are saved separately in `graph/labels.csv`. The whole historical graph is never fed indiscriminately to the GNN.

Missing last-submission values are filled with the **training median in the numeric feature matrix only**, and a missingness indicator is added. This does not invent an RDF submission or alter a CSV. The absence remains visible. The training-only pipeline then removes constant columns and standardizes values. Previous-attempt count is always zero in the temporal training cohort, so its effect cannot be learned there and it is removed from both models. Some future students are returning students; that remains a transfer limitation.

### 4. Why these techniques were chosen

**Training prevalence / majority baseline** uses no individual predictors. It assigns every row the training positive share, and at threshold 0.5 predicts successful for everyone. It provides the basic count/imbalance reference.

**Early-submission count baseline** ranks lower counts as greater risk. Its simple decision rule flags only zero-submission enrollments. The ranking and binary rule are deliberately explicit: two methods can use similar rankings but different thresholds and flag different numbers of cases.

**Logistic regression** is a small, inspectable tabular model. It learns a weighted combination of the permitted features. It uses balanced class weights, C=1 and a fixed threshold of 0.5. This gives a stronger baseline before claiming a graph neural network helps.

**GraphSAGE** follows the lab's message-passing idea. Two layers, each with 16 hidden dimensions, combine a node's own features with mean neighbor information. The implementation uses a bipartite PyTorch Geometric graph with enrollment/assessment node flags and edges in both directions. Neighbor assessment features are type, scheduled deadline and weight. It uses 100 epochs, Adam at 0.01 and a training-derived positive-class weight. There are no per-student identity embeddings.

For each split, the GNN's training graph includes only training enrollments and their permitted edges. The evaluation graph is separate. At inference, it can use other unlabeled enrollments in the same held-out cohort; it never receives their outcome labels or sends their messages through the training graph. Therefore this is cohort inference, not necessarily an isolated one-student-at-a-time service.

**TransE** follows the lab's embedding exercise: it learns vectors so head + relation is near tail. We use PyKEEN, dimension 32, 100 epochs, Adam at 0.01, batch size 256 and five sampled negatives per positive. It is compared with assessment popularity counted from training links only. Its library negative sampler corrupts entities and filters training positives; sampled unobserved links are training contrasts, not verified false statements under the open-world interpretation.

The [protocol](../config/learning/protocol.json) fixes settings and seeds. We did not search for a winning seed, tune the threshold on test labels or keep changing hyperparameters until a complex model won. Logistic regression is deterministic here; repeating its temporal fit with a different seed would not be a meaningful new experiment. GraphSAGE initialization and TransE partitions/training are each evaluated with seeds 0, 1 and 2.

### 5. Exact outcome results and how to read them

All rows below concern the same **340 test enrollments with 87 actual positives**:

| Method | Seed | Predicted unsuccessful | Average precision | Precision | Recall | Accuracy | Balanced accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | 0 | 137 | 0.526 | 40.9% | 64.4% | 67.1% | 66.2% |
| Training prevalence | 0 | 0 | 0.256 | 0.0% | 0.0% | 74.4% | 50.0% |
| Early submission count | 0 | 21 | 0.444 | 71.4% | 17.2% | 77.1% | 57.4% |
| GraphSAGE | 0 | 152 | 0.502 | 32.2% | 56.3% | 58.5% | 57.8% |
| GraphSAGE | 1 | 183 | 0.504 | 34.4% | 72.4% | 57.6% | 62.5% |
| GraphSAGE | 2 | 186 | 0.498 | 36.0% | 77.0% | 59.1% | 65.0% |

![Temporal average precision](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/classification-comparison.png)

**Average precision (AP)** summarizes how well actual positives occur near the top of the ranking. Here the constant-score AP is 87/340 = 0.256. The implementation uses scikit-learn's `average_precision_score`; it is not trapezoidal area under a precision-recall curve. GraphSAGE's mean is **0.502**, population standard deviation across seeds **0.002**, and range **0.498–0.504**. These three seeds do not form a confidence interval for performance on other cohorts.

**The logistic-regression counts:** it flags **137**, of which **56** really have unsuccessful outcomes and **81** are false positives. It misses **31** of the 87 actual positives. Its precision is 56/137 = **40.9%**; its recall is 56/87 = **64.4%**. It overcounts positives by 50, but that total alone hides both missed cases and false alarms.

**The submission rule:** it flags 21, correctly identifies 15, generates six false positives and misses 72 actual positives. Its precision is higher (**71.4%**) but its recall is only **17.2%**. This is why a simple rule can have better accuracy and still miss most of the target cases.

**The majority baseline:** it gets 253/340 = **74.4% accuracy** by predicting successful for everyone. It finds none of the 87 positive outcomes. Balanced accuracy is 0.5. Accuracy is therefore insufficient to judge this task. The count rule has 77.1% accuracy, while logistic regression trades some accuracy for greater recall.

**The GNN:** it flags between 152 and 186 cases across seeds. Its ranking is above the count baseline but below logistic regression here. The count feature already summarizes a central part of the graph structure; AAA has few shared assessment nodes. This is a plausible explanation for limited added value, not a causal conclusion established by this experiment.

![Confusion matrices](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/confusion-matrices.png)

Rows are observed classes and columns are predicted classes. The off-diagonal cells are mistakes. GraphSAGE seed 0 is shown because it was predefined, not selected as the best seed. Class-weighted outputs are not established calibrated risk probabilities, and 0.5 is a reproducible teaching threshold rather than an operationally optimized decision policy.

### 6. What the logistic coefficients mean

| Standardized feature | Coefficient |
|---|---:|
| registration_day | +0.464 |
| early_submission_count | -1.044 |
| early_late_count | +0.200 |
| last_submission_day | +0.484 |
| missingindicator_last_submission_day | -0.122 |

A positive coefficient raises the modeled log-odds of the combined unsuccessful label, holding the other inputs fixed; a negative coefficient lowers it. The strongest negative coefficient is the early-submission count. Registration-day and last-submission-day coefficients describe conditional associations, not causes. Correlated features, missingness handling, class weighting and the narrow cohort all affect interpretation. A coefficient is not an explanation of why a particular student withdrew.

### 7. The leakage control and random-split comparison

The deliberately invalid control supplies the final label itself as a predictor. It reaches AP=1.000 and exactly 87 predicted positives. That is a diagnostic example of cheating, not the best usable model; its outputs are labeled `INVALID label-leak control` and excluded from the valid-model comparison.

| Random split seed | Logistic AP | GraphSAGE AP | Students shared across train/test |
|---|---:|---:|---:|
| 0 | 0.671 | 0.618 | 7 |
| 1 | 0.461 | 0.420 | 10 |
| 2 | 0.551 | 0.472 | 13 |

Each random test has 211 rows and 51 positives, mixing offerings. Some random scores are higher and some lower than the temporal result. The important issue is what is being tested: these splits mix past/future and share student identities, so they cannot substantiate future-offering generalization. The headline evaluation instead uses 2013J for training and 2014J for testing, with student separation.

### 8. Exact link results: TransE versus the original count baseline

There are 3,149 assessment records in the source, including 42 banked results. We use the **3,107 unique nonbanked enrollment → assessment pairs** as observed links. Each seed keeps **2,487 training**, **310 validation** and **310 hidden test** links. Validation is reserved and participates in standard known-truth filtering during evaluation; there is no early stopping or hyperparameter selection.

Additional training support contains 772 facts: enrollment-to-offering, assessment-to-offering and assessment type. No AssessmentRecord nodes or inverse/reified paths remain that would directly reveal a hidden submission. Every candidate assessment and enrollment is represented through this metadata, so no hidden edge is dropped for a completely unknown entity. Some test enrollments have no remaining training submission links; these harder cases are retained and counted in each seed's summary.

Both methods rank the **same six scheduled assessments in the same offering**, including the exam for which this extract has no recorded results. The baseline score is the assessment's training submission count. IDs do not break ties: the evaluator uses average/realistic rank.

| Seed | Hidden links | Popularity MRR unfiltered | TransE MRR unfiltered | Popularity MRR filtered | TransE MRR filtered | Mean candidates after filtering |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 310 | 0.477 | 0.226 | 0.985 | 0.913 | 2.25 |
| 1 | 310 | 0.460 | 0.232 | 0.979 | 0.937 | 2.23 |
| 2 | 310 | 0.494 | 0.228 | 0.987 | 0.930 | 2.20 |

![Link comparison](../outputs/learning/runs/f7649738f7414536bc2395ef7496eebf/link-comparison.png)

**MRR** averages reciprocal rank: first place contributes 1, second 0.5, third 0.333. **Hits@1** and **Hits@3** count how often the true assessment is in the first position or first three positions; all values and per-link ranks are saved in the report. For six random candidate ranks, expected MRR is **0.408**, Hits@1 **0.167** and Hits@3 **0.500**.

Unfiltered evaluation retains all six alternatives, including other assessments the same enrollment truly submitted. Filtered evaluation removes those other known true links, while retaining the target. The complete truth is used for that scoring operation only; model training and popularity counts use training links. Filtering leaves only about two candidates on average, often the true assessment and an exam with no observed results. Its random-ranking MRR is already around **0.72**, not 0.408. This makes the high filtered scores much less surprising.

TransE's mean filtered MRR is **0.926** versus **0.984** for popularity. Its mean unfiltered MRR is **0.229** versus **0.477** for popularity. TransE is even below uniform random rank on the unfiltered task. Reporting only its high filtered number would obscure this weakness.

This graph is dense in mandatory assignment participation and has very few assessment candidates. Popularity captures much of that structure. We can conclude that these embeddings do not beat that baseline under this protocol. We cannot conclude that TransE never works or that an unobserved exam was not taken.

### 9. Challenges, fixes and remaining limits

| Challenge or observed issue | How it was handled |
|---|---|
| Historical graph contains outcomes and their OWL-derived classes | Use an explicit feature/edge allowlist and save labels separately. Tests change labels/grades in a graph copy and confirm unchanged classifier inputs. |
| Post-cutoff submissions or already-known withdrawals can give misleading results | Filter submission dates and eligibility at day 60. Test inclusion at day 60, exclusion at day 61, and banked-result exclusion. |
| Returning students cross the year boundary | Purge 26 eligible earlier enrollments; record all 36 original overlapping students and the resulting prevalence shift. |
| Previous-attempt count is constant in training | A preliminary run exposed the limitation. Add train-only variance filtering for both models and rerun the complete protocol; current evidence supersedes that prototype. No test-score-based feature selection was used. |
| Missing feature versus missing RDF fact | Impute only the numerical feature matrix using training statistics and a missingness flag; preserve source files and the label-free RDF. |
| PyKEEN initially tried writing its cache under a restricted home directory | Set `PYSTOW_HOME` to the ignored project `.runtime/learning/pystow` before importing PyKEEN; keep the same Conda environment. |
| CPU-only library warnings | Set an explicit evaluation batch size and disable training memory pinning. Library evaluation can still print CPU pinning/memory notices; the final run completed and all evidence checks passed. No GPU was required. |
| High filtered link scores can exaggerate difficulty | Show unfiltered scores, candidate-set sizes and a random-rank reference alongside filtered scores. |
| Complex models did not beat the stronger simple baselines | Report the loss transparently with all seeds, exact splits and predictions; do not select a favorable seed or tune on test results. |

There are only two offerings of one module and one temporal test. Random seeds measure training/split variability, not independent future cohorts. Submission/registration dates are availability proxies: the release lacks ingestion or revision timestamps. Assessment schedule metadata is treated as known in advance. The model excludes grades and click activity, so it is deliberately limited. The combined Fail/Withdrawn target does not identify causes or prescribe interventions. No operational decisions or automatic changes to historical outcomes are implemented.

### 10. Verification, provenance and how to rerun

The 21 learning checks cover source counts, independent CSV feature reconstruction, eligibility, cutoffs, banked records, forbidden labels, split integrity and stable inputs. The 54 saved-evidence checks recompute classification metrics from predictions, check preprocessing against training rows, verify link partitions and popularity ranks, and check input/output hashes and PROV-O entities. These are local learning checks; existing SHACL/integration CI does not run these new models.

Each execution gets a unique folder. It holds protocol, graph inputs, separate labels, cohort/split tables, predictions, coefficients, model checkpoints, per-link ranks, figures, a readable report, JSON summaries, verification and `provenance.ttl`. Failed runs retain `failure.json`; only a fully verified run updates `outputs/learning/latest.json`. The earlier prototype folder remains historical evidence; its original source fingerprints need not match the corrected current code.

```powershell
conda activate M2ENV
Set-Location 'D:\DESKTOP\M2\kr-oulad'
.\run-learning.ps1
```

To check saved evidence without retraining:

```powershell
python evaluation/verify_learning.py
```

To view the saved results:

```powershell
Start-Process '.\outputs\learning\learning-results.html'
```

The HTML report needs no running database. Model checkpoints (`.pt`) and runtime caches are ignored by Git; regenerate them after cloning before using the complete evidence verifier. Predictions and their interpretation remain separate from source facts and OWL inferences. Read [README section 14](../README.md#14-session-6--learning-and-baseline-comparisons) for the execution order and file roles, and [project provenance](project-provenance.html#13-session-6-learning-provenance) for the exact source graph and recorded software.

Course reference: [Session 6 lab](../../KRR/demos/session-06-learning/README.md). Method references: [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html), [average precision](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html), [GraphSAGE layer](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.SAGEConv.html), [PyKEEN TransE](https://pykeen.readthedocs.io/en/stable/api/pykeen.models.TransE.html), and [filtered ranking evaluation](https://pykeen.readthedocs.io/en/stable/tutorial/understanding_evaluation.html).

