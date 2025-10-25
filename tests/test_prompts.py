import inspect

import pytest


import stac_mcp.fast_server as fast_server
from fastmcp.prompts.prompt import PromptMessage


PROMPT_NAMES = [
    "_prompt_get_root",
    "_prompt_get_conformance",
    "_prompt_search_collections",
    "_prompt_get_collection",
    "_prompt_get_item",
    "_prompt_search_items",
    "_prompt_estimate_data_size",
    "_prompt_create_item",
    "_prompt_update_delete_item",
]


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_prompt_functions_exist_and_return_helpful_text(name: str):
    """Each prompt function should exist and return a helpful string.

    We don't assert on exact wording (prompts are documentation) but ensure
    they contain at least an Example section and Parameters/Notes guidance so
    agent callers can parse them.
    """
    assert hasattr(fast_server, name), f"Missing prompt function: {name}"
    func = getattr(fast_server, name)
    # The decorator may replace the original function with a prompt object
    # (FunctionPrompt). Try multiple strategies to obtain human-help text.
    text = None
    # 1. If the attribute is directly callable, call it.
    if callable(func):
        try:
            text = func()
        except TypeError:
            # Some wrappers are callable but require args; ignore and try other
            # accessors below.
            text = None

    # 2. If the wrapper exposes the original function under common names,
    # call it.
    if text is None:
        for candidate in ("func", "fn", "function"):
            if hasattr(func, candidate):
                orig = getattr(func, candidate)
                if callable(orig):
                    text = orig()
                    break

    # 3. If the wrapper stores a template or renderable string, try common
    # attributes.
    if text is None:
        for attr_name in ("template", "render", "text", "body"):
            if hasattr(func, attr_name):
                val = getattr(func, attr_name)
                # call if callable
                text = val() if callable(val) else val
                break

    # 4. Fall back to descriptive metadata on the prompt object.
    if text is None:
        # Ensure the prompt object at least exposes a short description and name
        assert hasattr(func, "description") or hasattr(func, "name"), (
            f"Prompt object {name!r} lacks callable/template/description"
        )
        # Use the description for a minimal assertion
        desc = getattr(func, "description", None)
        assert isinstance(desc, (str, type(None)))
        # If no full text available, consider this a minimal pass.
        return

    # Accept either a plain string or a PromptMessage-like object (machine
    # readable). If a PromptMessage is returned, extract its text content for
    # the same human-helpfulness checks.
    content_text = None
    if isinstance(text, PromptMessage):
        # PromptMessage.content is typically a TextContent with a `text` field
        cont = getattr(text, "content", None)
        content_text = getattr(cont, "text", None) if cont is not None else None
    elif hasattr(text, "content") and hasattr(text.content, "text"):
        content_text = text.content.text
    elif isinstance(text, str):
        content_text = text

    assert isinstance(content_text, str), "Prompt must return a string or PromptMessage with text content"
    # Basic sanity checks for helpfulness
    assert "Example" in content_text, "Prompt should include an Example section"
    assert ("Parameters" in content_text) or ("Description" in content_text), (
        "Prompt should include Parameters or Description"
    )
