import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_spell,
    find_nearby_places,
    generate_item_artwork,
    generate_item_video,
    generate_spell_gif,
    geocode_address,
    get_monster_stats,
    get_spell,
    roll_dice,
    search_spells,
)

PROJECT_ID = "qwiklabs-gcp-01-f77911216b85"
LOCATION = "us-central1"
MEMORY_BANK_ID = "1603219344936927232"

# Configure A2UI Schema Manager (v0.8) with BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Realm & Rune RPG Companion agent. You assist fantasy RPG players and Dungeon Masters "
        "by recalling user preferences across sessions, running Python code in a secure sandbox, generating item and creature artwork, "
        "generating short video showcases of magical items using Google Omni model, "
        "geocoding locations and discovering campaign map inspirations using Google Maps APIs, looking up D&D 5e monster stats, "
        "rolling virtual dice, and managing spellbook entries in Firestore."
    ),
    workflow_description="Analyze the request, execute tools if needed, and return structured A2UI UI when appropriate.",
    ui_description=(
        "Keep every surface clean, beautifully structured, and on-theme: ONE Card > ONE Column with structured children. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, Divider, Image, and Video. Do not use Table or Heading or Buttons. "
        "For monster stat cards, spell cards, and item cards: "
        "1. Place an Image at the top when available (e.g. `image_url` returned from `get_monster_stats` or `generate_item_artwork`). "
        "2. Add the title with `usageHint`: 'h2' (e.g., 'Owlbear' or 'Fireball'). "
        "3. Add a subtitle/category with `usageHint`: 'caption' (e.g., 'Large monstrosity, unaligned' or '3rd-level evocation'). "
        "4. Insert a Divider component between major sections. "
        "5. Structure core attributes into clean Row or Text components (e.g. 'Armor Class: 13 | Hit Points: 59 | Speed: 30 ft'). "
        "No raw markdown inside text values; rely on `usageHint` ('h1', 'h2', 'h3', 'h4', 'body', 'caption') for emphasis. "
        "Output ONLY the raw A2UI JSON array — no markdown fences, no conversational prose, and never wrap in <a2a_datapart_json> tags."
    ),
    include_schema=True,
    include_examples=True,
)


def _get_agent_engine_resource_name() -> str | None:
    possible_paths = [
        Path("deployment_metadata.json"),
        Path(__file__).parent.parent / "deployment_metadata.json",
    ]
    for path in possible_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    remote_id = data.get("remote_agent_runtime_id")
                    if remote_id:
                        return remote_id
            except Exception:
                pass
    return None


agent_engine_id = _get_agent_engine_resource_name()
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_id
)


async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


memory_service = memory_bank_service_builder()


def get_weather(query: str) -> str:
    """Simulates a web search. Use it to get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city or query to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        generate_item_artwork,
        generate_item_video,
        generate_spell_gif,
        geocode_address,
        find_nearby_places,
        get_monster_stats,
        roll_dice,
        search_spells,
        get_spell,
        add_spell,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
