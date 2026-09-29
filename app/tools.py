"""Tools for Realm & Rune RPG Companion (Firestore, Virtual Dice, D&D 5e API, Geocoding, Places, Image Gen)."""
import io
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request
import google.auth
from dotenv import load_dotenv
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types
from PIL import Image, ImageEnhance

# Load local .env variables
load_dotenv()

PROJECT_ID = "qwiklabs-gcp-01-f77911216b85"
BUCKET_NAME = "realm-and-rune-assets-qwiklabs-gcp-01-f77911216b85"


def _get_db():
    creds, _ = google.auth.default()
    return firestore.Client(project=PROJECT_ID, credentials=creds)


async def generate_item_artwork(prompt: str, tool_context: ToolContext) -> dict:
    """Generate high-quality fantasy RPG item, spell, creature, or weapon artwork using Imagen/Gemini.

    Saves the image into the agent playground artifacts and uploads it to public GCS storage.

    Args:
        prompt: Description of the fantasy item or artwork to generate (e.g., 'A glowing sword of dragon fire').
        tool_context: ADK tool execution context used to record artifacts in Playground.

    Returns:
        Dictionary containing the public HTTPS image URL and artifact metadata.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    try:
        # Generate image using gemini-3.1-flash-lite-image in global region
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        img_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    img_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not img_bytes:
            return {"error": "Failed to generate image bytes from model."}

        timestamp = int(time.time())
        slug = re.sub(r"[^a-z0-9]", "_", prompt.lower()[:25]).strip("_")
        filename = f"artwork_{slug}_{timestamp}.jpg"

        # 1. Save artifact to ADK Playground session
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        if tool_context:
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public GCS bucket
        creds, _ = google.auth.default()
        storage_client = storage.Client(project=PROJECT_ID, credentials=creds)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(img_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "prompt": prompt,
            "filename": filename,
            "public_url": public_url,
        }
    except Exception as e:
        return {"error": f"Image generation failed: {e}"}


async def generate_item_video(item_name: str, description: str, tool_context: ToolContext) -> dict:
    """Generate a short video showcasing an RPG item or artifact using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the video artifact with tool_context.save_artifact so it shows up in the Playground's Artifacts panel,
    and returns its public Cloud Storage https URL.

    Args:
        item_name: Name of the magical item, weapon, or artifact (e.g. 'Dragon Scale Shield', 'Vorpal Sword').
        description: Visual description or action prompt for the video.
        tool_context: ADK tool execution context used to save video artifacts in Playground.

    Returns:
        Dictionary containing status, filename, and public https URL.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    timestamp = int(time.time())
    slug = re.sub(r"[^a-z0-9]", "_", item_name.lower()).strip("_")
    filename = f"item_video_{slug}_{timestamp}.mp4"
    object_name = f"item_videos/{filename}"
    gcs_dest_path = f"gs://{BUCKET_NAME}/{object_name}"

    prompt = f"A short cinematic showcase video of the RPG item '{item_name}': {description}. Detailed fantasy item showcase, smooth motion."

    try:
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_format={"type": "video", "delivery": "uri", "gcs_uri": gcs_dest_path},
            timeout=180,
        )

        creds, _ = google.auth.default()
        storage_client = storage.Client(project=PROJECT_ID, credentials=creds)
        bucket = storage_client.bucket(BUCKET_NAME)

        blob = bucket.blob(object_name)
        if not blob.exists():
            blobs = list(bucket.list_blobs(prefix=f"item_videos/item_video_{slug}_{timestamp}"))
            if blobs:
                blob = blobs[0]
                object_name = blob.name

        video_bytes = blob.download_as_bytes()
        mime_type = "video/mp4"

        # 1. Save artifact in memory with tool_context.save_artifact
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Return public https URL
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"

        return {
            "status": "success",
            "item_name": item_name,
            "filename": filename,
            "public_url": public_url,
        }
    except Exception as e:
        return {"error": f"Video generation failed: {e}"}


def geocode_address(address: str) -> dict:
    """Convert a location or address string into latitude and longitude coordinates using Google Maps Geocoding API.

    Args:
        address: The address or location name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Eiffel Tower').

    Returns:
        Dictionary with key fields: 'address' (queried), 'formatted_address', and 'location' ({'lat': ..., 'lng': ...}).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    encoded_addr = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RealmAndRuneAgent/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") == "OK" and data.get("results"):
            res = data["results"][0]
            loc = res["geometry"]["location"]
            return {
                "name": address,
                "formatted_address": res.get("formatted_address"),
                "location": {"latitude": loc["lat"], "longitude": loc["lng"]},
            }
        return {"error": f"Geocoding failed for address '{address}': {data.get('status')}"}
    except Exception as e:
        return {"error": f"Failed to connect to Geocoding API: {e}"}


def find_nearby_places(
    latitude: float, longitude: float, place_type: str = "tourist_attraction", radius: float = 1000.0
) -> list[dict]:
    """Find nearby real-world places or campaign location inspirations near given coordinates using Places API (New).

    Args:
        latitude: Latitude coordinate of search center.
        longitude: Longitude coordinate of search center.
        place_type: Type of places to search for (e.g. 'tourist_attraction', 'park', 'museum', 'restaurant').
        radius: Search radius in meters (default 1000.0).

    Returns:
        List of matching places with key fields: 'name', 'address', and 'location' ({'latitude': ..., 'longitude': ...}).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius,
            }
        },
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    try:
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "Unknown")
            addr = place.get("formattedAddress", "N/A")
            loc = place.get("location", {})
            results.append({
                "name": name,
                "address": addr,
                "location": {"latitude": loc.get("latitude"), "longitude": loc.get("longitude")},
            })

        return results if results else [{"message": f"No nearby places found of type '{place_type}'."}]
    except Exception as e:
        return [{"error": f"Failed to query Places API (New): {e}"}]


async def get_monster_stats(monster_name: str, tool_context: ToolContext | None = None) -> dict:
    """Fetch real RPG monster stats, hit points, armor class, and actions from the public D&D 5e API, and generate creature artwork.

    Args:
        monster_name: Name of the monster to lookup (e.g. 'goblin', 'beholder', 'ancient red dragon').
        tool_context: Optional ADK tool execution context used to save image artifacts and upload artwork to GCS.

    Returns:
        Dictionary containing monster statistics, AC, HP, challenge rating, abilities, and generated image_url.
    """
    monster_id = monster_name.lower().strip().replace(" ", "-")
    url = f"https://www.dnd5eapi.co/api/2014/monsters/{monster_id}"

    headers = {"User-Agent": "RealmAndRuneAgent/1.0"}
    dnd_key = os.getenv("DND_API_KEY")
    if dnd_key:
        headers["Authorization"] = f"Bearer {dnd_key}"

    image_url = None
    if tool_context:
        art_res = await generate_item_artwork(
            f"Fantasy RPG illustration of a {monster_name}, epic creature artwork, highly detailed",
            tool_context,
        )
        if isinstance(art_res, dict) and "public_url" in art_res:
            image_url = art_res["public_url"]

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ac_info = data.get("armor_class", [])
            ac_val = ac_info[0].get("value") if ac_info and isinstance(ac_info[0], dict) else ac_info

            result = {
                "name": data.get("name"),
                "size": data.get("size"),
                "type": data.get("type"),
                "alignment": data.get("alignment"),
                "armor_class": ac_val,
                "hit_points": data.get("hit_points"),
                "hit_dice": data.get("hit_dice"),
                "speed": data.get("speed"),
                "challenge_rating": data.get("challenge_rating"),
                "xp": data.get("xp"),
                "actions": [
                    {"name": a.get("name"), "description": a.get("desc")} for a in data.get("actions", [])
                ],
                "special_abilities": [
                    {"name": sa.get("name"), "description": sa.get("desc")}
                    for sa in data.get("special_abilities", [])
                ],
            }
            if image_url:
                result["image_url"] = image_url
            return result
    except Exception as e:
        res = {"error": f"Monster '{monster_name}' not found in public database ({e})."}
        if image_url:
            res["image_url"] = image_url
        return res


def roll_dice(expression: str = "1d20") -> dict:
    """Roll virtual RPG dice using standard notation (e.g., '1d20', '8d6+5', '3d6-2').

    Args:
        expression: Dice notation string (e.g., '1d20', '3d6+2', '8d6'). Defaults to '1d20'.

    Returns:
        Dictionary containing individual rolls, modifier, total result, and a summary string.
    """
    clean_expr = expression.lower().replace(" ", "")
    match = re.match(r"^(\d*)d(\d+)([+-]\d+)?$", clean_expr)
    if not match:
        return {"error": f"Invalid dice expression '{expression}'. Expected format like '1d20', '3d6+2', or '8d6'."}

    num_dice = int(match.group(1)) if match.group(1) else 1
    num_sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if num_dice <= 0 or num_dice > 100 or num_sides <= 0 or num_sides > 1000:
        return {"error": "Number of dice must be between 1-100 and sides between 1-1000."}

    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    mod_str = f" {modifier:+d}" if modifier != 0 else ""
    summary = f"Rolled {expression}: {rolls}{mod_str} = {total}"

    return {
        "expression": expression,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "summary": summary,
    }


def search_spells(query: str = "", level: int | None = None, school: str | None = None) -> list[dict]:
    """Search or filter RPG spells in the Firestore database.

    Args:
        query: Optional text query to search in spell name or description.
        level: Optional spell level filter (0-9).
        school: Optional spell school filter (e.g. Evocation, Abjuration, Conjuration).

    Returns:
        List of matching spell dictionaries containing spell stats and details.
    """
    db = _get_db()
    spells_ref = db.collection("spells")

    docs = spells_ref.stream()
    results = []

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        # Apply filters
        if level is not None and data.get("level") != level:
            continue

        if school is not None and data.get("school", "").lower() != school.lower():
            continue

        if query:
            q = query.lower()
            name = data.get("name", "").lower()
            desc = data.get("description", "").lower()
            effect = data.get("damage_or_effect", "").lower()
            if q not in name and q not in desc and q not in effect:
                continue

        results.append(data)

    return results


async def generate_spell_gif(spell_name: str, description: str = "", tool_context: ToolContext | None = None) -> dict:
    """Generate a ~5-second animated boomerang GIF for an RPG spell lookup using Imagen and Pillow.

    Args:
        spell_name: Name of the spell (e.g. 'Fireball', 'Healing Word').
        description: Description of the spell effect.
        tool_context: Optional ADK tool context to record artifact in Playground.

    Returns:
        Dictionary containing public GCS URL of the generated boomerang GIF.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"Fantasy RPG magic spell illustration of {spell_name}: {description}. Glowing magical aura, epic spell energy effect."

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        img_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    img_bytes = part.inline_data.data
                    break

        if not img_bytes:
            return {"error": "Failed to generate base image for spell GIF."}

        base_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        base_img = base_img.resize((512, 512), Image.Resampling.LANCZOS)

        # Create ~5-second boomerang frames (20 frames forward + 18 frames reversed = 38 frames @ 130ms = ~5 sec)
        frames = []
        num_half = 20
        for i in range(num_half):
            factor = 1.0 + (i / float(num_half - 1)) * 0.40
            enhancer = ImageEnhance.Brightness(base_img)
            frame = enhancer.enhance(factor)
            color_enhancer = ImageEnhance.Color(frame)
            frame = color_enhancer.enhance(1.0 + (i / float(num_half - 1)) * 0.30)
            frames.append(frame)

        # Boomerang sequence
        boomerang_frames = frames + frames[-2:0:-1]

        gif_io = io.BytesIO()
        boomerang_frames[0].save(
            gif_io,
            format="GIF",
            save_all=True,
            append_images=boomerang_frames[1:],
            duration=130,
            loop=0,
        )
        gif_bytes = gif_io.getvalue()

        timestamp = int(time.time())
        slug = re.sub(r"[^a-z0-9]", "_", spell_name.lower()).strip("_")
        filename = f"spell_anim_{slug}_{timestamp}.gif"

        # Upload GIF to public GCS bucket
        creds, _ = google.auth.default()
        storage_client = storage.Client(project=PROJECT_ID, credentials=creds)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(gif_bytes, content_type="image/gif")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        if tool_context:
            artifact_part = types.Part.from_bytes(data=gif_bytes, mime_type="image/gif")
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        return {
            "status": "success",
            "spell_name": spell_name,
            "filename": filename,
            "public_url": public_url,
        }
    except Exception as e:
        return {"error": f"Failed to generate spell GIF: {e}"}


async def get_spell(spell_id: str, tool_context: ToolContext | None = None) -> dict:
    """Retrieve details for a specific RPG spell by its ID from Firestore, including an animated ~5s boomerang GIF.

    Args:
        spell_id: The unique identifier of the spell (e.g. 'fireball', 'healing-word').
        tool_context: Optional ADK tool execution context used to save image/GIF artifacts.

    Returns:
        Dictionary containing the spell's details and animated boomerang gif_url/image_url.
    """
    db = _get_db()
    doc_ref = db.collection("spells").document(spell_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id

        # Generate ~5s animated boomerang GIF for spell lookup
        gif_res = await generate_spell_gif(data.get("name", spell_id), data.get("description", ""), tool_context)
        if isinstance(gif_res, dict) and "public_url" in gif_res:
            data["image_url"] = gif_res["public_url"]
            data["gif_url"] = gif_res["public_url"]

        return data

    return {"error": f"Spell '{spell_id}' not found in database."}


def add_spell(
    spell_id: str,
    name: str,
    level: int,
    school: str,
    description: str,
    damage_or_effect: str = "",
    casting_time: str = "1 action",
    range: str = "60 feet",
) -> dict:
    """Add a new RPG spell or update an existing spell in the Firestore database.

    Args:
        spell_id: Unique identifier for the spell (e.g. 'counterspell').
        name: Display name of the spell (e.g. 'Counterspell').
        level: Spell level (0 for cantrips, 1-9 for leveled spells).
        school: Magic school (e.g. Abjuration, Evocation, Necromancy).
        description: Full text description of what the spell does.
        damage_or_effect: Brief description of damage or primary effect.
        casting_time: Time required to cast the spell (e.g. '1 action', '1 bonus action').
        range: Spell casting range (e.g. '60 feet', 'Self', 'Touch').

    Returns:
        Dictionary confirming the spell was saved successfully.
    """
    db = _get_db()
    spell_data = {
        "id": spell_id,
        "name": name,
        "level": level,
        "school": school,
        "description": description,
        "damage_or_effect": damage_or_effect,
        "casting_time": casting_time,
        "range": range,
    }

    doc_ref = db.collection("spells").document(spell_id)
    doc_ref.set(spell_data)

    return {"status": "success", "message": f"Spell '{name}' (ID: {spell_id}) successfully saved.", "spell": spell_data}
