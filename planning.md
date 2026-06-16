# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset for items that match the user's requested item type or style, then narrows by size and budget if those constraints are provided. It returns matching listing dictionaries sorted by a simple relevance score so the agent can confidently choose the top result for the next step.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A natural-language item request such as `"vintage graphic tee"` or `"brown cardigan for fall layering"`.
- `size` (str): The user's desired size, such as `"M"` or `"S/M"`. If `None`, the tool skips size filtering.
- `max_price` (float): The highest price the user is willing to pay. If `None`, the tool skips price filtering.

**What it returns:**
Returns `list[dict]`. Each dict is one listing from `data/listings.json` with the fields `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. The list is sorted best match first based on keyword overlap between the user description and the listing's title, description, category, style tags, brand, and colors.

**What happens if it fails or returns nothing:**
If no listings match, the tool returns an empty list instead of raising an exception. The agent stops the workflow, stores an `error_message` in session state, and tells the user that no items matched the description, size, and budget together; it then suggests a fallback such as raising the budget, removing the size filter, or broadening the description.

---

### Tool 2: suggest_outfit

**What it does:**
Uses the selected thrifted item plus the user's wardrobe to generate 1 to 2 realistic outfit suggestions. If the wardrobe is empty, it switches to general styling advice for the new item instead of pretending it has specific closet pieces to reference.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The listing selected from `search_listings`, including fields like `title`, `description`, `style_tags`, `price`, `colors`, `size`, and `platform`.
- `wardrobe` (dict): A wardrobe object with an `items` list. Each wardrobe item contains `id`, `name`, `category`, `colors`, `style_tags`, and optional `notes`.

**What it returns:**
Returns `str`. The string contains either specific outfit combinations that name pieces from the wardrobe, or general styling advice if the wardrobe is empty. The response should mention how the thrifted item pairs with bottoms, shoes, layers, or accessories and describe the vibe in natural language.

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty, the tool still returns a useful non-empty string with general styling ideas. If the LLM call fails or produces an empty response, the agent stores an `error_message`, returns a fallback message about how the item could be styled in broad terms, and does not crash the workflow.

---

### Tool 3: create_fit_card

**What it does:**
Turns the outfit suggestion and selected thrifted item into a short, shareable caption that sounds like a real outfit post. It should feel casual and specific, naturally mentioning the item, where it was found, and the overall look.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion returned by `suggest_outfit`.
- `new_item` (dict): The selected listing dict, used to reference the item name, price, brand if present, and selling platform.

**What it returns:**
Returns `str`. The string is a 2 to 4 sentence fit card or social caption that describes the outfit vibe and includes the thrifted piece naturally. It should vary across different inputs and avoid sounding like a store listing.

**What happens if it fails or returns nothing:**
If `outfit` is empty or only whitespace, the tool returns a descriptive error message string such as `"I couldn't create a fit card because no outfit suggestion was available yet."` The agent surfaces that message to the user and stops instead of generating a caption from incomplete context.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
The planning loop reads the current session state and decides the next action based on which required values already exist.

1. Parse the user request into three search inputs: `description`, `size`, and `max_price`. Also capture wardrobe context from the request or load a test wardrobe.
2. If `selected_item` is not in session state, call `search_listings(description, size, max_price)`.
3. After `search_listings` returns, check `results`.
4. If `results` is empty, set `error_message = "No listings found for that description, size, and price."`, return early, and show the user a suggestion to loosen one constraint.
5. If `results` is not empty, set `search_results = results` and `selected_item = results[0]`.
6. If `outfit_suggestion` is not in session state and `selected_item` exists, call `suggest_outfit(selected_item, wardrobe)`.
7. After `suggest_outfit` returns, check whether the returned string is empty after stripping whitespace.
8. If the outfit string is empty, set `error_message = "I found an item, but I couldn't generate an outfit suggestion."`, return early with a fallback explanation, and do not call `create_fit_card`.
9. If the outfit string is valid, set `outfit_suggestion` in session state.
10. If `fit_card` is not in session state and `outfit_suggestion` exists, call `create_fit_card(outfit_suggestion, selected_item)`.
11. After `create_fit_card` returns, store the result as `fit_card`.
12. The loop ends when either `fit_card` exists or `error_message` exists. The final response includes either the full result package or the failure message.

---

## State Management

**How does information from one tool get passed to the next?**
The agent keeps a single session dictionary for one interaction. That dictionary stores:

- `user_query`: the original natural-language request.
- `description`, `size`, `max_price`: parsed search constraints.
- `wardrobe`: the wardrobe dict used for styling.
- `search_results`: the full list returned by `search_listings`.
- `selected_item`: the top listing chosen from `search_results`.
- `outfit_suggestion`: the text returned by `suggest_outfit`.
- `fit_card`: the text returned by `create_fit_card`.
- `error_message`: a user-facing failure explanation if any step cannot continue.

State is passed forward by reading from and writing to this session dictionary. `selected_item` flows into `suggest_outfit`, and both `selected_item` and `outfit_suggestion` flow into `create_fit_card` without the user re-entering anything.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Return early with a message like: `"I couldn't find a match under $30 in size M. Try increasing your budget, removing the size filter, or describing the item more broadly."` |
| suggest_outfit | Wardrobe is empty | Continue with a general styling response instead of specific closet pairings, for example: `"You don't have wardrobe items saved yet, so here are a few ways to style this piece with basics you may already own."` |
| create_fit_card | Outfit input is missing or incomplete | Return an error string, surface it to the user, and stop the workflow instead of generating a vague caption from missing context. |

---

## Architecture

```mermaid
flowchart TD
    A[User query] --> B[Planning loop]
    B --> C[Parse description, size, max_price, wardrobe]
    C --> D[search_listings(description, size, max_price)]
    D --> E{Any matches?}
    E -- No --> F[Set error_message in session]
    F --> G[Return helpful no-results message]
    E -- Yes --> H[Session.selected_item = results[0]]
    H --> I[suggest_outfit(selected_item, wardrobe)]
    I --> J{Outfit text available?}
    J -- No --> K[Set error_message in session]
    K --> L[Return styling fallback or failure message]
    J -- Yes --> M[Session.outfit_suggestion = outfit text]
    M --> N[create_fit_card(outfit_suggestion, selected_item)]
    N --> O{Fit card created?}
    O -- No --> P[Set error_message in session]
    P --> Q[Return fit-card failure message]
    O -- Yes --> R[Session.fit_card = caption]
    R --> S[Return selected item, outfit suggestion, fit card]
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
- I will use Codex/ChatGPT to implement one function at a time in `tools.py`.
- For `search_listings`, I will provide the Tool 1 section from this file and the field list from `data/listings.json`, and ask for a pure-Python implementation using `load_listings()`. I expect filtering, relevance scoring, and empty-list behavior. I will verify it by checking that it filters by price and size, drops zero-score items, and returns a sorted `list[dict]`.
- For `suggest_outfit`, I will provide the Tool 2 section plus the wardrobe schema from `data/wardrobe_schema.json`. I expect prompt construction for both non-empty and empty wardrobes, a Groq LLM call, and a non-empty string result. I will verify that empty wardrobes still produce styling advice and that named wardrobe items appear when a wardrobe is present.
- For `create_fit_card`, I will provide the Tool 3 section and one sample `selected_item` plus sample `outfit_suggestion`. I expect a prompt that produces a short caption and guards against empty `outfit`. I will verify that empty input returns an error string and that repeated runs vary enough to feel natural.

**Milestone 4 — Planning loop and state management:**
- I will use Codex/ChatGPT with the Planning Loop, State Management, Error Handling table, and Mermaid diagram from this file.
- I expect it to produce an `agent.py` or equivalent function that creates a session dictionary, calls the tools conditionally, stores intermediate values, and stops early on failures.
- Before trusting the generated code, I will verify that it does not call all tools unconditionally, that it stores `selected_item`, `outfit_suggestion`, and `fit_card` in session state, and that every early-return branch matches the failure behavior described above.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the request into `description="vintage graphic tee"`, `size=None`, and `max_price=30.0`. It also captures wardrobe context matching baggy jeans and chunky sneakers, then calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`.

**Step 2:**
`search_listings` returns one or more matching listing dicts, likely including the faded bootleg-style graphic tee at `$24` from Depop. The agent stores the full results list as `search_results`, stores the first item as `selected_item`, and calls `suggest_outfit(selected_item, wardrobe)`.

**Step 3:**
`suggest_outfit` returns a string describing 1 to 2 outfit options using the selected tee with the user's baggy jeans and chunky sneakers, possibly adding a denim jacket or crossbody bag for layering. The agent stores that string as `outfit_suggestion` and calls `create_fit_card(outfit_suggestion, selected_item)`.

**Step 4:**
`create_fit_card` returns a short caption such as a thrift-find post that mentions the graphic tee, the `$24` price, and Depop in a natural way. The agent stores that result as `fit_card` and ends the workflow.

**Final output to user:**
The user sees:

- The top item match with key details such as title, price, size, condition, and platform.
- A short outfit suggestion using their wardrobe context.
- A final fit card caption they could copy into a post or story.
