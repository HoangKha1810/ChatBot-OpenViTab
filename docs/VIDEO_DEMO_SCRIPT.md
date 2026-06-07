# Suggested Video Demo Flow

1. Open `http://127.0.0.1:8000`.
2. Show the status pill with the real dataset count: 329 tables and the train/dev/test QA counts.
3. Choose a real QA from the left sidebar.
4. Point at the table preview and explain that the rows come from Open-ViTabQA, not mock data.
5. Press **Chạy pipeline**.
6. Show the final answer, expected answer, confidence score, Models tab, SQL tab, evidence tab, and verifier tab.
7. Use these stable demo cases:

| Split | QA ID | Why it is good for demo |
| --- | --- | --- |
| dev | `56_3_238` | Superlative reasoning: tallest building -> number of floors. |
| dev | `23_4_88` | Merged header handling: episode title -> time-slot rank. |
| test | `99932_2_90` | Numeric cell lookup: 3.500 thousand coffee bags -> country. |
| test | `99921_1_43` | Rank lookup: rank 5 -> city. |
| test | `9990_2_27` | Compound numeric yes/no: year 2020 and percentage below 66. |
| test | `99917_3_67` | Header-threshold reasoning: column `≥150m` contains count 3. |

Suggested narration:

> The system does not answer directly from a free-form prompt. It uses lightweight local models for schema linking, text-to-SQL, answer synthesis, and verification, then executes SQL against a real SQLite table, returns evidence rows, verifies support, and shows a confidence score.
