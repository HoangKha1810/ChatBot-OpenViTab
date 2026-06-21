# Canva AI Prompt: 60-Slide Dissertation Deck

Copy the full prompt below into Canva AI / Canva Docs to Design. If Canva rejects the prompt for length, paste it in three batches: slides 1-20, slides 21-40, and slides 41-60.

```text
Create a complete 60-slide academic presentation deck for an undergraduate final-year project viva/defence.

Deck title:
Research on a SQL-Grounded Multi-Agent Model for Vietnamese Table Question Answering

Student:
Nguyễn Huỳnh Hoàng Kha
BSc (Hons) Computer Science
CMP6200/DIG6200 Individual Undergraduate Project
Supervisors: Nguyễn Lưu Thuỳ Ngân, Đặng Văn Thìn
Date: June 2026

Design requirements:
- Use a polished academic technology style.
- 16:9 widescreen slides.
- White or very light background, dark navy text, blue accent colour.
- Use diagrams, flow arrows, metric cards, charts, and simple database/table icons.
- Avoid cartoon style. Avoid marketing language.
- Keep each slide readable with concise bullets.
- Use speaker-note style short narration where helpful.
- Use visual hierarchy: title, key message, evidence/detail.
- Include slide numbers.
- Include placeholders for screenshots of the demo UI, SQL trace, evidence rows, and progress tab.
- Do not invent university logos; use placeholders where needed.
- The deck should be detailed enough to explain the full dissertation, but still structured for an oral presentation.

Important project facts to use:
- Topic: Vietnamese Table Question Answering (TableQA).
- Core problem: direct LLMs can produce fluent but unsupported answers from tables.
- Dataset: Open-ViTabQA.
- Data split mentioned in the report: 7,928 train, 991 validation, 992 test.
- Final demo dataset in app: 329 tables shown in UI.
- Proposed solution: SQL-grounded multi-agent architecture.
- Pipeline: Vietnamese question → table normalisation → SQLite database → schema linking → query planning → text-to-SQL → SQL execution → evidence rows → answer synthesis → verifier → confidence score → final answer.
- Current demo models: bge-m3 for schema linking, qwen2.5-coder:14b for text-to-SQL, qwen2.5:7b for answer synthesis and advisory verification.
- Evaluation metrics: EM, F1, grounding score, unsupported answer rate, SQL validity, SQL execution success, SQL semantic accuracy, empty retrieval rate, verifier catch rate, mean latency, median latency, trace completeness.
- Final improved results: EM = 0.586, F1 = 0.674, grounding = 0.904, unsupported answer rate = 4.6%, SQL validity = 98.4%, SQL execution success = 95.7%, SQL semantic accuracy = 91.6%, empty retrieval rate = 3.7%, verifier catch rate = 86.5%, mean latency = 2.0s, median latency = 1.8s, trace completeness = 96.0%.
- Full SQL-grounded multi-agent before final improvement: EM = 0.548, F1 = 0.636, grounding = 0.869, unsupported answer rate = 7.1%.
- Baselines: LLaMA 8B zero-shot, LLaMA 8B + LoRA, LLaMA 8B + QLoRA, Text-to-SQL + main LLM, Multi-agent without verifier, Full SQL-grounded multi-agent.
- Baseline numbers:
  - LLaMA 8B zero-shot: EM 0.000, F1 0.077, grounding 0.281, unsupported 42.8%.
  - LLaMA 8B + LoRA: EM 0.436, F1 0.500, grounding 0.684, unsupported 19.2%.
  - LLaMA 8B + QLoRA: EM 0.419, F1 0.487, grounding 0.667, unsupported 20.7%.
  - Text-to-SQL + main LLM: EM 0.491, F1 0.579, grounding 0.792, unsupported 12.4%.
  - Multi-agent without verifier: EM 0.517, F1 0.603, grounding 0.829, unsupported 9.8%.
  - Full SQL-grounded multi-agent: EM 0.548, F1 0.636, grounding 0.869, unsupported 7.1%.
- Improvement changes:
  - EM +0.038.
  - F1 +0.038.
  - Grounding +0.035.
  - Unsupported answer rate -2.5 percentage points.
  - SQL validity +1.3 percentage points.
  - SQL execution success +3.3 percentage points.
  - SQL semantic accuracy +4.8 percentage points.
  - Empty retrieval rate -3.2 percentage points.
  - Verifier catch rate +10.5 percentage points.
  - Mean latency -0.3s.
  - Median latency -0.3s.
- Error reductions per 1,000 validation queries:
  - Schema linking mistakes: 38 to 22.
  - SQL execution failures: 76 to 43.
  - Empty retrieval: 69 to 37.
  - Unsupported final answers: 71 to 46.
  - Verifier missed inconsistencies: 17 to 8.
  - Low-confidence flagged answers: 0 to 18, which is good because uncertainty is surfaced.

Create these exact 60 slides:

Slide 1 — Title
Title: Research on a SQL-Grounded Multi-Agent Model for Vietnamese Table Question Answering
Content: student name, course, supervisors, date.
Visual: clean title slide with subtle table/grid and SQL flow motif.

Slide 2 — One-Sentence Thesis
Title: Main Claim
Content: “For Vietnamese TableQA, better answers come from controlling the evidence path, not from asking a language model to infer everything from a long table prompt.”
Add three supporting phrases: executable SQL, retrieved evidence, verifier and confidence trace.
Visual: one strong quote-style slide.

Slide 3 — Why TableQA Matters
Content: Real-world information is often stored in tables: rankings, dates, measurements, financial values, categories, and short labels. Users want to ask natural-language questions over these tables.
Visual: examples of table types: education, business, public information, analytics.

Slide 4 — What Is Table Question Answering?
Content: Define TableQA as answering a natural-language question from structured or semi-structured table evidence. Explain that it is harder than paragraph QA because it may require filtering, lookup, comparison, aggregation, max/min, and row-level reasoning.
Visual: question bubble pointing to a table.

Slide 5 — Vietnamese TableQA Context
Content: Vietnamese TableQA is lower-resource than English TableQA. Vietnamese tables introduce diacritics, abbreviations, aliases, mixed units, and short cell values. The project uses Open-ViTabQA as the benchmark dataset.
Visual: Vietnamese question examples over table columns.

Slide 6 — The Practical Problem
Content: Direct LLM prompting can generate fluent answers but may not reveal whether the answer came from the correct row or cell. Fluency is not the same as evidence-grounded correctness.
Visual: split screen: “sounds right” versus “proved by evidence”.

Slide 7 — Problem Statement
Content: Current LLM-based Vietnamese TableQA approaches can produce plausible answers from linearised tables, but they remain hard to debug and vulnerable to unsupported outputs when questions require filtering, comparison, aggregation, or interpreting ambiguous Vietnamese headers.
Visual: warning triangle over an unsupported answer.

Slide 8 — Research Aim
Content: Design, implement, and evaluate a SQL-grounded multi-agent architecture that improves answer accuracy, grounding, and interpretability for Vietnamese TableQA.
Visual: aim statement with three pillars: accuracy, grounding, interpretability.

Slide 9 — Objectives
Content:
1. Preprocess Open-ViTabQA tables.
2. Implement zero-shot, LoRA, and QLoRA baselines.
3. Develop table-to-database and text-to-SQL pipeline.
4. Integrate coordinator, verifier, and answer synthesis modules.
5. Improve reliability using schema linking, repair, planning, confidence scoring, routing, caching, and tests.
6. Evaluate with accuracy, grounding, operational, and interpretability metrics.
Visual: numbered objective ladder.

Slide 10 — Scope
Content: Included: Vietnamese TableQA, Open-ViTabQA tables, table parsing, normalisation, SQLite conversion, SQL generation, execution, evidence retrieval, answer synthesis, verification, confidence, logging, benchmarking, and demo UI. Excluded: new large-scale dataset creation, production deployment, human-subject testing, and open-domain document QA.
Visual: in-scope/out-of-scope two-column layout.

Slide 11 — Contributions
Content:
- A traceable SQL-grounded multi-agent architecture.
- A modular pipeline for schema linking, SQL generation, evidence retrieval, verification, and answer synthesis.
- Evaluation across baselines and ablations.
- Improved grounding and unsupported-answer behaviour.
- A browser demo that exposes SQL, evidence, verifier, and confidence.
Visual: five contribution cards.

Slide 12 — Literature Theme: Semi-Structured TableQA
Content: Semi-structured TableQA often requires compositional reasoning: filtering, comparison, arithmetic, and multi-step operations. WikiTableQuestions motivates table-specific reasoning beyond simple lookup.
Visual: small conceptual map of table operations.

Slide 13 — Literature Theme: Text-to-SQL
Content: WikiSQL and Spider show that natural-language questions can be translated into executable queries. This supports the project’s SQL-mediated design, but Vietnamese tables add schema linking and header ambiguity challenges.
Visual: natural language → SQL → rows.

Slide 14 — Literature Theme: Vietnamese Low-Resource QA
Content: Vietnamese QA has fewer resources than English. Open-ViTabQA is important because it provides a Vietnamese table-based benchmark. Vietnamese headers may contain aliases, abbreviations, units, and diacritic variation.
Visual: “low-resource constraints” with data/table icons.

Slide 15 — Literature Theme: LoRA and QLoRA
Content: LoRA and QLoRA make model adaptation cheaper than full fine-tuning. They are useful baselines, but adaptation alone does not guarantee row-level evidence grounding.
Visual: parameter-efficient tuning diagram.

Slide 16 — Literature Theme: Retrieval and Factuality
Content: Retrieval-grounded generation reduces unsupported outputs by connecting generation to evidence. For TableQA, evidence should be exact returned rows/cells, not only retrieved passages.
Visual: evidence lock icon over SQL rows.

Slide 17 — Literature Theme: Modular/Multi-Agent Systems
Content: A multi-agent system is useful when one model call is forced to perform too many responsibilities. In this project, agents are concrete technical modules: planner, text-to-SQL, executor, verifier, coordinator, answer synthesiser, and confidence scorer.
Visual: modular pipeline blocks.

Slide 18 — Research Gap
Content: Vietnamese TableQA needs an architecture that combines natural-language understanding, schema-aware SQL generation, executable evidence retrieval, verification, confidence estimation, and answer synthesis. The gap is a systems gap, not only a model-size gap.
Visual: gap bridge diagram.

Slide 19 — Project Justification
Content: A trustworthy TableQA system should show where the answer came from. SQL makes the evidence boundary explicit. Verification and confidence provide safer answer discipline. Trace logging allows errors to be assigned to specific modules.
Visual: “trust = evidence + trace + verification”.

Slide 20 — Methodology
Content: The project follows a design science and experimental computing approach: build artefact, test baselines, analyse errors, improve modules, evaluate quantitatively and qualitatively.
Visual: iterative loop: design → implement → evaluate → improve.

Slide 21 — Dataset: Open-ViTabQA
Content: Open-ViTabQA provides Vietnamese questions over tables. The report uses processed splits: 7,928 training items, 991 validation items, and 992 test items. The demo app displays 329 real tables.
Visual: dataset split cards.

Slide 22 — Dataset Challenges
Content: Tables include noisy headers, short labels, mixed units, merged headers, numeric values, rankings, dates, categories, and Vietnamese-specific wording. These require normalisation and schema linking before SQL can be reliable.
Visual: messy table transformed into clean schema.

Slide 23 — Preprocessing
Content: Source tables are parsed into standard table objects. Headers are normalised, rows are indexed, metadata is stored, and original header links are preserved so SQL results can be explained.
Visual: preprocessing pipeline.

Slide 24 — Table-to-Database Conversion
Content: Each table is converted into a relational representation. The system creates SQL-ready column names, key-normalised text fields, numeric fields, row indexes, and SQLite database files per table.
Visual: table → SQLite database icon.

Slide 25 — Overall Architecture
Content: Vietnamese question → Open-ViTabQA table → table normalisation → SQLite database → schema linker → query planner → text-to-SQL → SQL execution → evidence rows → answer synthesis → verifier → confidence → final answer.
Visual: central full architecture diagram.

Slide 26 — Three-Layer Design
Content:
Layer 1: database generation.
Layer 2: question planning and executable retrieval.
Layer 3: AI reasoning, verification, confidence, and answer generation.
Visual: three stacked layers.

Slide 27 — Component Responsibility Matrix
Content: Components and outputs:
Dataset ingestion → processed tables.
Table-to-database → schema and indexed rows.
Query planner → structured plan.
Text-to-SQL → auditable SQL.
SQL execution → evidence rows.
Verifier → pass/fail and reasons.
Answer synthesis → grounded answer.
Confidence logging → trace and confidence.
Visual: matrix/table.

Slide 28 — Query Planner
Content: The query planner identifies intent, target column, filter column, operation, answer type, sort direction, and numeric values. This narrows the SQL generation problem.
Visual: planning form object.

Slide 29 — Schema Linking
Content: Schema linking resolves Vietnamese aliases, abbreviations, and unit variation before SQL generation. The current demo uses bge-m3 embeddings to rank relevant columns.
Visual: question terms connected to column headers.

Slide 30 — Text-to-SQL Agent
Content: The text-to-SQL agent converts the Vietnamese question and schema context into SQL. The demo uses qwen2.5-coder:14b. SQL is guarded: unsafe SQL is rejected and deterministic candidates are retained when they already have evidence.
Visual: prompt → SQL code block.

Slide 31 — SQL Execution
Content: SQL is executed against SQLite. The result is not a vague text retrieval; it is a set of exact rows and cells. Execution success and empty-result rates become measurable diagnostics.
Visual: SQL query returning highlighted rows.

Slide 32 — SQL Repair and Recovery
Content: SQL validation and repair handle syntax errors, invalid column names, missing quotes, simple operator mistakes, and empty result recovery. This improves validity and execution success.
Visual: broken SQL → repair loop → executable SQL.

Slide 33 — Evidence Packaging
Content: Retrieved rows are packaged as evidence for answer synthesis and verification. Evidence rows are displayed in the demo so users can inspect why the answer was produced.
Visual: evidence card with row index and cell values.

Slide 34 — Answer Synthesis
Content: The answer synthesis model receives the question, query plan, and evidence rows. It is instructed to answer only from evidence, not from the full table or external knowledge. The demo uses qwen2.5:7b.
Visual: evidence rows → short Vietnamese answer.

Slide 35 — Evidence-Aware Verifier
Content: The verifier checks whether the answer logically follows from retrieved evidence. It covers lookup, comparison, aggregation, numeric calculation, max/min selection, filtering consistency, and coverage.
Visual: verifier checklist.

Slide 36 — Confidence Scoring
Content: Confidence combines SQL validity, execution success, evidence coverage, verifier result, repair status, and answer support. Low-confidence answers are surfaced instead of hidden.
Visual: confidence meter.

Slide 37 — Traceability
Content: The system logs plan, SQL, evidence rows, verifier output, confidence factors, model trace, repair notes, and final answer. Trace completeness reaches 96.0% in final evaluation.
Visual: trace timeline.

Slide 38 — Demo Interface
Content: The FastAPI browser demo shows real table, selected QA, progress, model trace, SQL trace, evidence rows, verifier result, confidence, and answer. No mock data is used.
Visual: placeholder screenshot of UI with labelled areas.

Slide 39 — Demo Runtime
Content: Recommended GPU demo machine: RTX A5000 24GB or similar, Ubuntu 22.04/24.04, 16GB+ RAM, 50GB+ disk. Demo models: bge-m3, qwen2.5-coder:14b, qwen2.5:7b. Launcher: python3 scripts/run_gpu_demo.py.
Visual: GPU/server setup cards.

Slide 40 — Implementation Stages
Content:
1. Dataset pipeline.
2. Baseline systems.
3. Database-grounded workflow.
4. Multi-agent control.
5. Technical improvements: schema linking, SQL repair, query planning, verifier v2, confidence, routing, caching, tests.
Visual: timeline from preprocessing to final demo.

Slide 41 — Baseline Systems
Content: Baselines test whether model prompting or adaptation alone can solve the problem: LLaMA 8B zero-shot, LoRA, QLoRA, text-to-SQL + main LLM, multi-agent without verifier, full SQL-grounded multi-agent.
Visual: baseline ladder.

Slide 42 — Evaluation Metrics
Content:
EM: strict answer exactness.
F1: partial answer overlap.
Grounding: evidence support.
Unsupported rate: plausible but unsupported answers.
SQL validity: syntactically valid SQL.
Execution success: query can run.
Latency: usability.
Trace completeness: interpretability.
Visual: metric glossary.

Slide 43 — Baseline Results Table
Content: Use this table:
Zero-shot: EM 0.000, F1 0.077, grounding 0.281, unsupported 42.8%.
LoRA: EM 0.436, F1 0.500, grounding 0.684, unsupported 19.2%.
QLoRA: EM 0.419, F1 0.487, grounding 0.667, unsupported 20.7%.
Text-to-SQL + main LLM: EM 0.491, F1 0.579, grounding 0.792, unsupported 12.4%.
Multi-agent without verifier: EM 0.517, F1 0.603, grounding 0.829, unsupported 9.8%.
Full SQL-grounded: EM 0.548, F1 0.636, grounding 0.869, unsupported 7.1%.
Visual: table plus small bar chart.

Slide 44 — What The Baselines Show
Content: Fine-tuning improves over zero-shot, but unsupported answers remain. SQL-grounded variants improve because they constrain the reasoning space and expose intermediate states. The verifier reduces unsupported outputs.
Visual: trend arrow from prompt-only to evidence-grounded.

Slide 45 — Full System Before Final Improvement
Content: Full SQL-grounded multi-agent system achieves EM 0.548, F1 0.636, grounding 0.869, unsupported 7.1%, SQL validity 97.1%, execution success 92.4%, mean latency 2.3s, median latency 2.1s.
Visual: metric cards.

Slide 46 — Final Improved Results
Content: Final improved system achieves EM 0.586, F1 0.674, grounding 0.904, unsupported 4.6%, SQL validity 98.4%, execution success 95.7%, SQL semantic accuracy 91.6%, empty retrieval 3.7%, verifier catch rate 86.5%, mean latency 2.0s, median latency 1.8s.
Visual: big metric dashboard.

Slide 47 — Before vs After Improvement
Content:
EM +0.038.
F1 +0.038.
Grounding +0.035.
Unsupported answer rate -2.5 pp.
SQL validity +1.3 pp.
Execution success +3.3 pp.
SQL semantic accuracy +4.8 pp.
Empty retrieval -3.2 pp.
Verifier catch +10.5 pp.
Mean latency -0.3s.
Visual: before/after bar chart.

Slide 48 — Technical Improvement Modules
Content:
Schema linking.
SQL repair loop.
Query planner.
Verifier v2.
Confidence scoring.
Adaptive routing.
Caching and rule checks.
Unit tests.
Visual: eight-module improvement grid.

Slide 49 — Module Contribution View
Content:
Schema linking improves SQL semantic accuracy and EM.
SQL repair improves validity and execution success.
Query planning improves intent focus.
Verifier v2 improves grounding and unsupported rate.
Confidence scoring flags uncertainty.
Adaptive routing improves descriptive-answer quality.
Caching reduces latency.
Unit tests prevent regressions.
Visual: module-to-metric mapping.

Slide 50 — Ablation Analysis
Content:
No SQL retrieval: EM 0.468, F1 0.553; grounding weakens.
No verifier: EM 0.517, F1 0.603; unsupported answers reappear.
No coordinator re-plan: EM 0.505, F1 0.592; first-pass errors are not corrected.
Full system: EM 0.548, F1 0.636; best balance.
Visual: ablation table.

Slide 51 — Error Taxonomy
Content: Errors are separated into schema linking mistakes, SQL generation errors, execution failures, empty retrieval, verifier misses, confidence issues, and final answer formatting. This makes debugging possible.
Visual: error taxonomy tree.

Slide 52 — Diagnostic Error Reduction
Content:
Schema mistakes: 38 → 22 per 1,000.
SQL execution failures: 76 → 43.
Empty retrieval: 69 → 37.
Unsupported final answers: 71 → 46.
Verifier missed inconsistencies: 17 → 8.
Low-confidence flagged answers: 0 → 18.
Visual: red-to-green reduction chart.

Slide 53 — Example Demo Case
Content: QA ID 56_3_238. Question: “Tòa nhà có chiều cao cao nhất có bao nhiêu tầng?” Table: “Danh sách tòa nhà cao nhất Thành phố New York_4”. Expected answer: 110.
Visual: screenshot placeholder of selected question and table.

Slide 54 — Example Trace
Content: Example pipeline: schema linker ranks height/floor columns, planner detects superlative, SQL orders numeric height descending or floor-related value depending on table schema, execution returns evidence row, answer synthesis outputs “110”, verifier checks evidence, confidence is high.
Visual: mini trace with Plan → SQL → Evidence → Answer.

Slide 55 — Strengths
Content:
Traceability: plan, SQL, evidence, verifier, confidence.
Grounding: answers are constrained by retrieved rows.
Modularity: components can be replaced independently.
Debuggability: failures are assigned to pipeline stages.
Demo transparency: UI exposes the reasoning path.
Visual: strengths cards.

Slide 56 — Weaknesses and Limitations
Content:
More modules mean more engineering complexity.
Incorrect table conversion can still cause semantically wrong SQL.
Schema linking remains difficult for noisy Vietnamese headers.
Verification and repair add latency.
Validated on Open-ViTabQA-style tables, not every Vietnamese table format.
Visual: limitations table.

Slide 57 — Impact
Content: Academic impact: reframes Vietnamese TableQA as a representation, retrieval, and verification problem, not only an adaptation problem. Practical impact: supports trustworthy natural-language access to tabular information in education, public information lookup, business reporting, and internal analytics.
Visual: two-column academic/practical impact.

Slide 58 — Future Work
Content:
Test larger and noisier Vietnamese table collections.
Expand Vietnamese alias and abbreviation resources.
Evaluate verifier independently with labelled mismatch examples.
Improve adaptive routing for descriptive questions.
Add human evaluation of trustworthiness.
Compare with newer open models.
Visual: roadmap arrow.

Slide 59 — References and Foundations
Content: Include key references in compact form:
Open-ViTabQA dataset.
Pasupat and Liang, WikiTableQuestions.
Zhong et al., WikiSQL / Seq2SQL.
Yu et al., Spider.
Hu et al., LoRA.
Dettmers et al., QLoRA.
Lewis et al., RAG.
Huang et al. and Wang et al., LLM factuality.
Zhu et al., LLM-enhanced text-to-SQL survey.
Visual: reference wall / citation strip.

Slide 60 — Final Conclusion
Content: The final conclusion is that Vietnamese TableQA benefits when the system controls the evidence path. The proposed SQL-grounded multi-agent architecture improves accuracy, grounding, unsupported-answer behaviour, and interpretability compared with direct prompting or fine-tuning alone. Final takeaway: the answer should not only be fluent; it should be executable, evidenced, verified, and traceable.
Visual: final architecture fading into “Evidence-grounded answers for Vietnamese tables”. Add “Thank you / Questions”.
```

