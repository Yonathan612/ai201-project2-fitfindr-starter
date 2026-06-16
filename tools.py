"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()
_GROQ_MODEL = "llama-3.3-70b-versatile"
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "i",
    "im",
    "in",
    "is",
    "it",
    "like",
    "looking",
    "me",
    "my",
    "of",
    "on",
    "please",
    "something",
    "that",
    "the",
    "to",
    "want",
    "with",
}


def _tokenize(text: str) -> set[str]:
    """Normalize free text into lowercase search tokens."""
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOPWORDS
    }


def _size_matches(listing_size: str, requested_size: str) -> bool:
    """Allow flexible matching such as M against S/M or M/L."""
    listing_normalized = listing_size.lower()
    requested_normalized = requested_size.lower().strip()
    return (
        requested_normalized in listing_normalized
        or listing_normalized in requested_normalized
    )


def _format_listing(item: dict) -> str:
    """Format a listing dict into a compact prompt-friendly summary."""
    brand = item.get("brand") or "Unknown brand"
    return (
        f"{item['title']} | category: {item['category']} | size: {item['size']} | "
        f"price: ${item['price']:.2f} | colors: {', '.join(item['colors'])} | "
        f"style tags: {', '.join(item['style_tags'])} | brand: {brand} | "
        f"platform: {item['platform']} | description: {item['description']}"
    )


def _call_groq(prompt: str, temperature: float) -> str:
    """Call Groq chat completions and return the stripped text response."""
    client = _get_groq_client()
    completion = client.chat.completions.create(
        model=_GROQ_MODEL,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a stylist for secondhand fashion. "
                    "Be concrete, tasteful, and natural."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return (completion.choices[0].message.content or "").strip()


def _score_listing(listing: dict, query_tokens: set[str], raw_description: str) -> int:
    """Score a listing with higher weight on title and style-tag matches."""
    title_tokens = _tokenize(listing["title"])
    description_tokens = _tokenize(listing["description"])
    category_tokens = _tokenize(listing["category"])
    style_tokens = _tokenize(" ".join(listing["style_tags"]))
    color_tokens = _tokenize(" ".join(listing["colors"]))
    brand_tokens = _tokenize(listing["brand"] or "")

    score = 0
    score += len(query_tokens & title_tokens) * 4
    score += len(query_tokens & style_tokens) * 3
    score += len(query_tokens & category_tokens) * 2
    score += len(query_tokens & description_tokens)
    score += len(query_tokens & color_tokens)
    score += len(query_tokens & brand_tokens)

    raw_query = raw_description.lower().strip()
    title_text = listing["title"].lower()
    style_text = " ".join(listing["style_tags"]).lower()

    if raw_query and raw_query in title_text:
        score += 8
    elif raw_query and raw_query in style_text:
        score += 5

    return score


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query_tokens = _tokenize(description)
    scored_results: list[tuple[int, dict]] = []

    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue

        if size is not None and not _size_matches(listing["size"], size):
            continue

        score = _score_listing(listing, query_tokens, description)

        if score == 0:
            continue

        scored_results.append((score, listing))

    scored_results.sort(
        key=lambda result: (
            -result[0],
            result[1]["price"],
            result[1]["title"].lower(),
        )
    )
    return [listing for _, listing in scored_results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = wardrobe.get("items", [])
    item_summary = _format_listing(new_item)

    if not wardrobe_items:
        prompt = f"""
You are helping a user style a secondhand item without access to their closet.

New item:
{item_summary}

Write 1 to 2 short outfit suggestions in natural language.
- Give general styling advice with basics a person may already own.
- Mention bottoms, shoes, and optional layer or accessory ideas.
- Keep it practical and specific to the item's vibe.
- Do not mention that data is missing.
"""
        try:
            response = _call_groq(prompt, temperature=0.6)
            if response:
                return response
        except Exception:
            pass

        return (
            f"Try the {new_item['title']} with relaxed denim or trousers, simple shoes, "
            "and one easy layer so the thrifted piece stays the focus."
        )

    wardrobe_summary = "\n".join(
        [
            (
                f"- {item['name']} | category: {item['category']} | "
                f"colors: {', '.join(item['colors'])} | "
                f"style tags: {', '.join(item['style_tags'])} | "
                f"notes: {item.get('notes') or 'None'}"
            )
            for item in wardrobe_items
        ]
    )

    prompt = f"""
You are styling a thrifted item using the user's real wardrobe pieces.

New item:
{item_summary}

Wardrobe items:
{wardrobe_summary}

Write 1 to 2 outfit suggestions.
- Explicitly name the wardrobe pieces you are using.
- Build complete looks with tops/bottoms/shoes and optional layers or accessories.
- Explain the vibe briefly.
- Keep the response under 140 words total.
"""
    try:
        response = _call_groq(prompt, temperature=0.7)
        if response:
            return response
    except Exception:
        pass

    featured_items = ", ".join(item["name"] for item in wardrobe_items[:3])
    return (
        f"Style the {new_item['title']} with pieces you already own like {featured_items}. "
        "Build one look around contrast in shape and another around matching its overall vibe."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "I couldn't create a fit card because no outfit suggestion was available yet."

    brand = new_item.get("brand") or "an unbranded find"
    prompt = f"""
Write a 2 to 4 sentence social caption for a thrifted outfit post.

Item details:
- title: {new_item['title']}
- price: ${new_item['price']:.2f}
- platform: {new_item['platform']}
- brand: {brand}
- colors: {', '.join(new_item['colors'])}

Outfit idea:
{outfit}

Requirements:
- Sound casual and authentic, not like a product listing.
- Mention the item title, price, and platform exactly once each in a natural way.
- Capture the outfit vibe with specific language.
- Do not use hashtags or bullet points.
"""
    try:
        response = _call_groq(prompt, temperature=1.0)
        if response:
            return response
    except Exception:
        pass

    return (
        f"Found the {new_item['title']} on {new_item['platform']} for ${new_item['price']:.2f} "
        f"and built the whole look around it. {outfit.strip()}"
    )
