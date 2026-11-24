# KAN-39: Gradio Usability Testing — FinWiseIQ

**Owner:** Frontend developer (Nasyitah)  
**Test date:** To be entered when the integrated app is tested  
**Target:** 27 November 2026  
**Environment:** Windows / browser / `python -m app.interface` (existing version), plus `python -m app.finwiseiq_redesign` (updated design)

## Scope

This task verifies that the **real** FinWiseIQ Gradio interface is usable after PR #18 connects it to the retrieval + OpenAI pipeline. It covers clarity, efficiency, readable citations, input validation, error handling, visual consistency, and responsiveness.

## Evidence already supplied by the team (not independently re-tested here)

Nurin reported that the existing frontend's **12 tests pass**, the pipeline returns answers with sources, and out-of-scope questions are refused. These are team-reported outcomes, **not** direct KAN-39 usability measurements.

## Offline redesign checks — automatically tested

- `python -m pytest tests/test_finwiseiq_redesign.py -q` : **13 passed**, using an injected **mock responder** (no live OpenAI calls).
- Checked message formatting, unchanged citation text, empty input, error redaction, clear button handler, quick question list, logo assets, mobile CSS, and reduced-motion support.
- These tests prove standalone UI logic only. **They do not prove** that the integrated backend runs or answers correctly.

## Manual usability checklist for the actual integrated app

After PR #18 is merged into `main`, run the app with a legitimate `.env` on your computer (never commit `.env`). For each case, fill in Observed and Status **after performing it**.

| ID | Scenario | Expected result | Observed | Status |
|---|---|---|---|---|
| U01 | Open updated app using `python -m app.finwiseiq_redesign` | Page loads, new logo and layout visible | Not run | Pending |
| U02 | Enter “What is Murabahah financing?” and press Enter | User question shown; backend answer includes appropriate source | Not run | Pending |
| U03 | Use the Send button for “What is Islamic banking?” | Same result as Enter; no duplicate message | Not run | Pending |
| U04 | Click the “Islamic vs conventional banking” suggested prompt | Text sent; grounded answer or an honest knowledge fallback | Not run | Pending |
| U05 | Send only spaces / blank input | Helpful validation; no API request | Not run | Pending |
| U06 | Ask “Which stock should I buy today?” | Politely refuses personalized investment advice | Not run | Pending |
| U07 | Ask an unrelated question such as “What is the weather today?” | Appropriate fallback; no invented answer | Not run | Pending |
| U08 | Ask a follow-up after an initial question | Earlier messages remain; answer appears in the right order | Not run | Pending |
| U09 | Select Clear after several messages | Chat cleared; input emptied; no console crash | Not run | Pending |
| U10 | Turn off / invalidate API credentials locally (do not screenshot secret) | Friendly error; no key or traceback displayed | Not run | Pending |
| U11 | Browser at approximately 390px wide (mobile DevTools) | No horizontal page overflow; inputs and chips usable | Not run | Pending |
| U12 | Use keyboard (Tab / Enter), and OS reduced-motion mode | Focus visible; input accessible; animation reduced | Not run | Pending |

## Time-on-task / observation fields

Complete during testing, preferably with a teammate acting as a first-time user:

| UX indicator | Observation |
|---|---|
| Find chat input without instructions | Pending |
| Submit one question successfully | Pending |
| Locate source / citation in reply | Pending |
| Identify that this is educational, not professional advice | Pending |
| Clear and restart a conversation | Pending |
| Confusing UI elements or suggested improvements | Pending |

## Evidence to attach

- Screenshot of starting screen (new logo and visual design)
- Screenshot of one successful answer with source (hide API secrets)
- Screenshot of an out-of-scope refusal
- Screenshot of mobile layout (DevTools at ~390px width)
- Final `pytest` command output, and any actual user feedback

## Conclusion

**Status: Pending real-environment verification.** The design implementation and 13 offline UI unit tests are prepared, but KAN-39 should only be marked Done after U01–U12 have been executed on the integrated application and the table updated with real observations.
