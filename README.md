# FitFindr

FitFindr is a multi-tool AI agent for secondhand fashion. It takes a natural-language query, finds a matching thrift listing from the mock dataset, suggests how to style that item with a user's wardrobe, and generates a short shareable fit card.

## What the agent does

The agent coordinates three required tools:

1. `search_listings(description, size, max_price)`
   Searches `data/listings.json`, filters by optional size and price, scores matches by keyword overlap, and returns ranked listing dictionaries.
2. `suggest_outfit(new_item, wardrobe)`
   Uses Groq's `llama-3.3-70b-versatile` model to suggest 1 to 2 outfits based on the selected thrift item and the user's wardrobe.
3. `create_fit_card(outfit, new_item)`
   Uses the same model to turn the selected item and outfit suggestion into a short social-style caption.

## Planning loop

The agent loop lives in `agent.py` and follows this sequence:

1. Initialize session state with the original query, parsed filters, wardrobe, and empty tool outputs.
2. Parse the query with regex to extract:
   - item description
   - optional size
   - optional max price
3. Call `search_listings(...)`.
4. If no search results are returned, stop immediately and store an error message in session state.
5. Otherwise, choose `results[0]` as `selected_item`.
6. Call `suggest_outfit(selected_item, wardrobe)`.
7. If an outfit suggestion is empty, stop and return an error.
8. Call `create_fit_card(outfit_suggestion, selected_item)`.
9. Return the completed session dictionary.

This is a real planning loop because later steps only run if earlier tool outputs are valid.

## State management

The session dictionary stores all state for a single run:

- `query`
- `parsed`
- `search_results`
- `selected_item`
- `wardrobe`
- `outfit_suggestion`
- `fit_card`
- `error`

This allows `selected_item` to flow from search into styling, and both `selected_item` and `outfit_suggestion` to flow into fit-card generation without asking the user again.

## Error handling

Each tool handles its own failure mode:

- `search_listings`
  Returns `[]` if nothing matches. The agent stops early and tells the user to broaden the query, remove size, or raise the budget.
- `suggest_outfit`
  If the wardrobe is empty, it still returns general styling advice instead of failing.
  If the Groq call fails, it falls back to a local styling string.
- `create_fit_card`
  If the outfit string is empty, it returns a descriptive error string instead of crashing.
  If the Groq call fails, it falls back to a local caption string.

## Files

- `tools.py`: tool implementations
- `agent.py`: planning loop and session state
- `app.py`: Gradio interface
- `planning.md`: tool specs, architecture, walkthrough, and AI tool plan
- `tests/test_tools.py`: unit tests for tool behavior and agent flow

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Create `.env` in the repo root:

```env
GROQ_API_KEY=your_key_here
```

## Run

CLI trial:

```bash
.venv/bin/python agent.py
```

Gradio app:

```bash
.venv/bin/python app.py
```

## Test

Run the current test suite with:

```bash
.venv/bin/python -m pytest tests/test_tools.py
```

## Current status

- `planning.md` is fully filled out
- all three required tools are implemented
- the agent loop is wired into the Gradio app
- tests pass locally

## Known limitation

The search ranking is functional but still simple. For some queries, a loosely related top may outrank the most intuitive fashion match. Improving relevance ranking is the next highest-value polish step before a final demo.
