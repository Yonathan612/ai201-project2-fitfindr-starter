from agent import run_agent
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)

    assert isinstance(results, list)
    assert len(results) > 0
    assert results[0]["category"] == "tops"


def test_search_respects_size_and_price_filters():
    results = search_listings("track jacket", size="M", max_price=50)

    assert len(results) > 0
    assert all(item["price"] <= 50 for item in results)
    assert all("m" in item["size"].lower() for item in results)


def test_search_returns_empty_list_when_no_matches():
    results = search_listings("sequined cowboy astronaut cape", size="XS", max_price=10)

    assert results == []


def test_suggest_outfit_uses_general_styling_for_empty_wardrobe(monkeypatch):
    monkeypatch.setattr(
        "tools._call_groq",
        lambda prompt, temperature: "Pair it with loose denim and simple sneakers for an easy everyday look.",
    )
    item = search_listings("graphic tee", max_price=30)[0]

    result = suggest_outfit(item, get_empty_wardrobe())

    assert "denim" in result.lower()


def test_suggest_outfit_references_wardrobe_items(monkeypatch):
    monkeypatch.setattr(
        "tools._call_groq",
        lambda prompt, temperature: (
            "Wear it with Baggy straight-leg jeans, dark wash and Chunky white sneakers "
            "for a relaxed streetwear look."
        ),
    )
    item = search_listings("graphic tee", max_price=30)[0]

    result = suggest_outfit(item, get_example_wardrobe())

    assert "Baggy straight-leg jeans" in result
    assert "Chunky white sneakers" in result


def test_create_fit_card_rejects_empty_outfit():
    item = search_listings("graphic tee", max_price=30)[0]

    result = create_fit_card("   ", item)

    assert result.startswith("I couldn't create a fit card")


def test_create_fit_card_returns_caption(monkeypatch):
    monkeypatch.setattr(
        "tools._call_groq",
        lambda prompt, temperature: (
            "Found the Graphic Tee — 2003 Tour Bootleg Style on depop for $24 and built the whole look around it. "
            "The loose denim and sneakers keep it worn-in and easy."
        ),
    )
    item = search_listings("graphic tee", max_price=30)[0]

    result = create_fit_card("Loose denim and sneakers keep it relaxed.", item)

    assert "depop" in result.lower()
    assert "$24" in result


def test_run_agent_sets_error_when_no_results():
    session = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )

    assert session["error"] is not None
    assert session["selected_item"] is None


def test_run_agent_happy_path(monkeypatch):
    monkeypatch.setattr(
        "agent.suggest_outfit",
        lambda item, wardrobe: "Wear it with Baggy straight-leg jeans, dark wash and Chunky white sneakers.",
    )
    monkeypatch.setattr(
        "agent.create_fit_card",
        lambda outfit, item: "Found a solid vintage tee look and turned it into a full outfit post.",
    )

    session = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )

    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["outfit_suggestion"] is not None
    assert session["fit_card"] is not None
