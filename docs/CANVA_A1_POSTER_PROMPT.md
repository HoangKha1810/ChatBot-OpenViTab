# Canva AI Prompt: A1 Research Poster

Copy the full prompt below into Canva AI / Canva Docs to Design. Ask Canva to create a polished academic A1 poster and export it as PDF.

```text
Create a professional A1 academic research poster in portrait orientation.

Design style:
- Clean university research poster, modern but formal.
- Use a white background with dark navy text and blue accents.
- Use a clear 3-column grid.
- Include subtle table/database/SQL visual motifs, but do not make it look like a marketing poster.
- Use readable poster typography: large title, clear section headers, compact body text, strong metric cards.
- Include diagrams/icons for: Vietnamese question, table, schema linking, SQL generation, SQL execution, evidence rows, verifier, final answer.
- Include one central architecture flow diagram.
- Include one results comparison chart and one compact metric table.
- Leave space for a QR code placeholder labelled “Demo / GitHub”.
- Do not invent university logos. Use placeholder text where logos are required.

Poster title:
Research on a SQL-Grounded Multi-Agent Model for Vietnamese Table Question Answering

Author block:
Nguyễn Huỳnh Hoàng Kha
BSc (Hons) Computer Science
CMP6200/DIG6200 Individual Undergraduate Project
Supervisors: Nguyễn Lưu Thuỳ Ngân, Đặng Văn Thìn
Date: June 2026

Visible poster text must be around 1,000 words (+/-10%). Use the exact content below as the poster copy, reorganised visually into poster sections.

SECTION 1 — Abstract
This project investigates Vietnamese Table Question Answering (TableQA), where a system must answer natural-language questions using evidence from tables. Direct large language model prompting can produce fluent answers, but those answers are difficult to audit and may be unsupported when questions require filtering, comparison, aggregation, temporal reasoning, or interpretation of abbreviated Vietnamese headers. The project therefore designs and evaluates a SQL-grounded multi-agent architecture that separates table representation, query planning, SQL generation, SQL execution, evidence verification, confidence scoring, and answer synthesis into inspectable modules. The final improved system reaches EM = 0.586, F1 = 0.674, grounding score = 0.904, unsupported answer rate = 4.6%, SQL validity = 98.4%, SQL execution success = 95.7%, and mean latency = 2.0 seconds.

SECTION 2 — Research Problem
Vietnamese TableQA is a low-resource task with specific linguistic and structural challenges. Tables may contain diacritics, abbreviations, mixed units, shortened headers, inconsistent formatting, and short cell values. A direct prompt-only model often treats the table as plain text, which makes it hard to know whether the final answer came from the correct row or cell. The central problem is that current LLM-based approaches can sound correct while remaining difficult to debug and vulnerable to unsupported outputs.

SECTION 3 — Aim and Objectives
The aim is to design, implement, and evaluate a SQL-grounded multi-agent architecture that improves answer accuracy, evidence grounding, and interpretability for Vietnamese TableQA. The objectives are: preprocess Open-ViTabQA tables into a stable representation; implement zero-shot, LoRA, and QLoRA baselines; develop table-to-database conversion and text-to-SQL retrieval; integrate coordinator, verifier, and answer synthesis agents; improve reliability through schema linking, SQL repair, query planning, confidence scoring, adaptive routing, caching, and tests; and evaluate the artefact using accuracy, grounding, operational, and interpretability metrics.

SECTION 4 — Research Gap
The literature shows that prompt engineering is flexible but weak for auditability, fine-tuning improves dataset familiarity but does not guarantee row-level evidence, classic text-to-SQL is useful but sensitive to noisy schemas, and general retrieval-augmented generation does not automatically enforce table operations such as max/min or aggregation. The gap is therefore a systems gap: Vietnamese TableQA needs natural-language understanding, schema-aware SQL generation, executable evidence retrieval, verification, confidence estimation, and answer synthesis in one traceable pipeline.

SECTION 5 — Proposed Architecture
The artefact has three layers. First, the database generation layer converts source tables into relational structures with SQL-ready columns, row indexes, metadata, and links back to original headers. Second, the question planning and executable retrieval layer transforms the Vietnamese question into a structured query plan, generates SQL, executes it, and returns evidence rows. Third, the AI reasoning layer verifies the evidence, coordinates repair or re-planning where needed, and generates the final answer from retrieved evidence rather than from the full table.

Central architecture flow diagram:
Vietnamese question → Open-ViTabQA table → table normalisation → SQLite database → schema linker → query planner → text-to-SQL agent → SQL execution → evidence rows → answer synthesis → verifier → confidence score → final grounded answer with trace.

SECTION 6 — Implementation
The implementation evolved from direct LLM baselines into a database-grounded system. Each Open-ViTabQA table is parsed, normalised, indexed, and converted into SQLite. The current demo uses real data and local Ollama models: bge-m3 for multilingual schema linking, qwen2.5-coder:14b for text-to-SQL, and qwen2.5:7b for answer synthesis and advisory verification. The FastAPI web demo displays the question, real table, model trace, SQL trace, evidence rows, verifier result, confidence score, and final answer.

SECTION 7 — Evaluation Method
The system is evaluated using both answer-quality and operational metrics. Exact Match measures strict answer correctness after normalisation. F1 captures partial lexical overlap. Grounding score measures evidence support. Unsupported answer rate tracks plausible answers not backed by retrieved evidence. SQL validity and SQL execution success test whether the intermediate query representation works. Latency measures usability, and trace completeness measures interpretability.

SECTION 8 — Results
Baseline comparison shows a clear improvement as the system becomes more evidence-grounded. LLaMA 8B zero-shot achieves EM = 0.000 and F1 = 0.077, with unsupported answer rate = 42.8%. LoRA improves to EM = 0.436 and F1 = 0.500, while QLoRA reaches EM = 0.419 and F1 = 0.487. A text-to-SQL plus main LLM variant reaches EM = 0.491 and F1 = 0.579. The full SQL-grounded multi-agent system reaches EM = 0.548, F1 = 0.636, grounding = 0.869, and unsupported answer rate = 7.1%. After final improvements, the system reaches EM = 0.586, F1 = 0.674, grounding = 0.904, unsupported answer rate = 4.6%, SQL validity = 98.4%, SQL execution success = 95.7%, and mean latency = 2.0 seconds.

Metric cards:
EM: 0.586
F1: 0.674
Grounding: 0.904
Unsupported answers: 4.6%
SQL validity: 98.4%
SQL execution success: 95.7%
Mean latency: 2.0s
Trace completeness: 96.0%

SECTION 9 — Key Contributions
The main contribution is not simply using a larger model. It is a traceable architecture where schema representation, executable retrieval, verification, confidence estimation, and final answer generation are separated into measurable responsibilities. This supports error attribution: wrong answers can be traced to schema linking, SQL generation, retrieval, verification, confidence estimation, or final formatting. The artefact demonstrates that Vietnamese TableQA benefits from controlling the evidence path rather than asking the final language model to infer everything from a long table prompt.

SECTION 10 — Limitations and Future Work
The prototype is validated on Open-ViTabQA-style tables and may not generalise to all Vietnamese table formats. It depends on correct table conversion and schema linking; a valid SQL query can still retrieve wrong evidence if the schema is wrong. Verification and repair improve trust but add complexity. Future work should test larger and noisier Vietnamese table collections, expand Vietnamese alias resources, evaluate the verifier with labelled mismatch examples, improve adaptive routing for descriptive questions, and explore broader user evaluation of trustworthiness.

SECTION 11 — Demo Artefact
The demo application runs on real Open-ViTabQA data with no mock data and no training required. It shows the live pipeline: Progress, Models, SQL, Evidence, Verifier, confidence, and final answer. Example question: “Tòa nhà có chiều cao cao nhất có bao nhiêu tầng?” The system returns the answer from SQL-executed evidence rows rather than unsupported free-form generation.

Final poster footer:
Repository: https://github.com/HoangKha1810/ChatBot-OpenViTab
Dataset: Open-ViTabQA
Keywords: Vietnamese TableQA, Text-to-SQL, SQL-grounded reasoning, multi-agent systems, evidence verification, low-resource NLP
```

