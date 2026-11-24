# KAN-33: Frontend Test Results

Date: 17 November 2026

## Objective
Test the FinWiseIQ Gradio chatbot independently using mock backend responses.

## Test Command
python -m pytest tests/test_interface.py -v

## Test Results
- Total tests: 12
- Passed: 12
- Failed: 0
- Execution time: 10.92 seconds

## Features Tested
1. Empty and invalid user input
2. Chat interaction and response display
3. Chat history handling
4. Backend exception handling
5. Empty and invalid backend responses

## Issues Found
No issues were found during the automated mock-based tests.

## Limitation
The tests use a mock backend. Integration with the actual
RAG and OpenAI backend has not been tested yet.

## Conclusion
All 12 automated frontend tests passed. The interface response
handling is ready for the next integration phase.

## Frontend UI polish verification

Verified on 24 November 2026 with Python 3.12 on Windows and Chrome. Launch the branded app from the repository root.

```powershell
.\.venv\Scripts\python.exe -m app.finwiseiq_redesign
```

- The chat heading and welcome text use light colors. Assistant bubbles are navy and user bubbles are teal. Chrome rendered light paragraph and list text alongside an underlined sample citation.
- At 390 × 844, the input used 16 px text, Send and Clear aligned in a single row with 44 px targets, and the page fit the viewport while a long sample citation wrapped.
- The question field has an accessible label. Tab moved through Send, Clear, and the first suggested question with visible focus. Chrome's reduced-motion emulation disabled the message animation. Clear restored the welcome text.
- Standalone English and Malay greetings return a local reply. Finance questions with a greeting still go through the existing responder. Blank submissions keep a single consecutive validation notice.

The full suite returned **58 passed**, including 24 redesign tests.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The browser layout checks used a mock finance answer. The automated cases verify greeting routing, Gradio's formatted history, repeated blank submissions, and existing response and error handling.

### Malay and mixed-language retrieval

A local retrieval check used the existing 0.45 threshold and the cached embedding model.

| Prompt | Top match | Similarity |
|---|---|---:|
| What is Murabahah financing? | IFC-001, Murabahah financing | 1.0000 |
| Apa itu pembiayaan Murabahah? | IFC-010, Mudarabah | 0.5468 |
| Murabahah financing tu camne? | IFC-001, Murabahah financing | 0.7618 |

The Malay prompt retrieved the wrong topic at rank 1, while the mixed-language example retrieved the intended topic. These checks cover retrieval only. Finance questions continue to use the existing retrieval and generation pipeline.
