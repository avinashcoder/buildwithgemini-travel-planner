# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


MODEL = "gemini-3.6-flash"

# Hardcoded project ID string for Firestore client (avoids project number lookup bug on Agent Platform)
FIRESTORE_PROJECT = "qwiklabs-gcp-04-b8d4bf5ff8b0"
_db: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client pinned to the explicit project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db


# --- Firestore Tools ---

def list_destinations(category: Optional[str] = None, max_results: int = 10) -> list[dict[str, Any]]:
    """Lists destination catalogs from Firestore.
    
    Args:
        category: Optional category filter (e.g., 'Nature & Adventure', 'Culture & Heritage', 'Art & Romance').
        max_results: Maximum number of destinations to retrieve (default 10).

    Returns:
        A list of destination dictionaries with details such as city, country, tags, budget, and highlights.
    """
    db = get_firestore_client()
    query = db.collection("destinations")
    if category:
        query = query.where("category", "==", category)

    docs = query.limit(max_results).stream()
    destinations = []
    for doc in docs:
        destinations.append(doc.to_dict())
    return destinations


def search_destinations(keyword: str) -> list[dict[str, Any]]:
    """Searches destination catalogs in Firestore by keyword matching city, country, summary, or tags.

    Args:
        keyword: The search word or phrase (e.g. 'temple', 'hiking', 'romantic', 'Japan', 'waterfall').

    Returns:
        A list of matching destinations.
    """
    db = get_firestore_client()
    docs = db.collection("destinations").stream()
    kw = keyword.lower()
    matches = []
    for doc in docs:
        data = doc.to_dict()
        searchable_text = " ".join([
            data.get("city", ""),
            data.get("country", ""),
            data.get("category", ""),
            data.get("summary", ""),
            " ".join(data.get("tags", [])),
            " ".join(data.get("highlights", [])),
        ]).lower()
        if kw in searchable_text:
            matches.append(data)
    return matches


def save_destination(
    city: str,
    country: str,
    category: str,
    summary: str,
    recommended_days: int = 3,
    estimated_budget_per_day_usd: int = 150,
    best_season: str = "Year-round",
    highlights: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Adds or updates a travel destination in the Firestore destinations collection.

    Args:
        city: City or destination name (e.g., 'Kyoto', 'Barcelona').
        country: Country name (e.g., 'Japan', 'Spain').
        category: Category (e.g., 'Culture & Heritage', 'Beach & Relaxation', 'Food & Wine').
        summary: Short narrative summary of the destination.
        recommended_days: Ideal stay duration in days.
        estimated_budget_per_day_usd: Estimated average daily cost per person in USD.
        best_season: Best time of year to visit.
        highlights: Key attractions or experiences to do there.
        tags: Keywords/tags for search and categorization.

    Returns:
        A dictionary with the save status and stored destination ID.
    """
    db = get_firestore_client()
    doc_id = f"{city.lower().replace(' ', '-')}-{country.lower().replace(' ', '-')}"
    doc_data = {
        "id": doc_id,
        "city": city,
        "country": country,
        "category": category,
        "summary": summary,
        "recommended_days": recommended_days,
        "estimated_budget_per_day_usd": estimated_budget_per_day_usd,
        "best_season": best_season,
        "highlights": highlights or [],
        "tags": tags or [],
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    db.collection("destinations").document(doc_id).set(doc_data, merge=True)
    return {"status": "success", "id": doc_id, "city": city, "country": country}


def save_traveler_itinerary(
    destination_city: str,
    trip_title: str,
    days: int,
    itinerary_plan: str,
    traveler_name: str = "traveler",
) -> dict[str, Any]:
    """Saves a generated trip itinerary to the Firestore 'itineraries' collection.

    Args:
        destination_city: Name of the destination city.
        trip_title: Catchy title for the trip.
        days: Duration in days.
        itinerary_plan: Detailed day-by-day plan or text summary.
        traveler_name: Name or handle of the traveler.

    Returns:
        Status and the created itinerary ID.
    """
    db = get_firestore_client()
    doc_ref = db.collection("itineraries").document()
    doc_data = {
        "destination_city": destination_city,
        "trip_title": trip_title,
        "days": days,
        "itinerary_plan": itinerary_plan,
        "traveler_name": traveler_name,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref.set(doc_data)
    return {"status": "success", "itinerary_id": doc_ref.id, "trip_title": trip_title}


# --- Auxiliary Utility Tools ---

def get_current_time(city: str) -> str:
    """Gets the current local time for major destination cities.

    Args:
        city: City name (e.g., 'Paris', 'Kyoto', 'Reykjavik', 'San Francisco').

    Returns:
        Current time string with timezone.
    """
    tz_map = {
        "paris": "Europe/Paris",
        "kyoto": "Asia/Tokyo",
        "tokyo": "Asia/Tokyo",
        "reykjavik": "Atlantic/Reykjavik",
        "santorini": "Europe/Athens",
        "athens": "Europe/Athens",
        "banff": "America/Edmonton",
        "san francisco": "America/Los_Angeles",
        "sf": "America/Los_Angeles",
    }
    key = city.strip().lower()
    tz_name = tz_map.get(key)
    if not tz_name:
        return f"Timezone information is not configured for {city}."
    tz = ZoneInfo(tz_name)
    now = datetime.datetime.now(tz)
    return f"Current time in {city.title()} is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}."


def get_live_destination_weather(city: str) -> dict[str, Any]:
    """Fetches real-time live weather conditions and temperature for any destination city.

    Args:
        city: City or destination name (e.g., 'Kyoto', 'Paris', 'Reykjavik', 'Banff', 'Santorini').

    Returns:
        A dictionary with the resolved location, current temperature in Celsius, humidity, wind speed, and weather condition.
    """
    import json
    import urllib.parse
    import urllib.request

    try:
        # 1. Geocode city name to coordinates using Open-Meteo Geocoding API
        encoded_city = urllib.parse.quote(city.strip())
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "TravelPlanner/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            geo_data = json.loads(response.read().decode())

        results = geo_data.get("results")
        if not results:
            return {"status": "error", "message": f"Could not find coordinates for city: {city}"}

        match = results[0]
        lat, lon = match["latitude"], match["longitude"]
        place_name = f"{match.get('name')}, {match.get('country', '')}"

        # 2. Fetch live weather using Open-Meteo Forecast API
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        )
        req_weather = urllib.request.Request(weather_url, headers={"User-Agent": "TravelPlanner/1.0"})
        with urllib.request.urlopen(req_weather, timeout=5) as response:
            w_data = json.loads(response.read().decode())

        current = w_data.get("current", {})
        temp_c = current.get("temperature_2m")
        temp_f = round((temp_c * 9 / 5) + 32, 1) if temp_c is not None else None

        # Simplified WMO weather code descriptions
        code = current.get("weather_code", 0)
        condition = "Clear sky" if code == 0 else "Partly cloudy / Overcast" if code in [1, 2, 3] else "Foggy" if code in [45, 48] else "Rainy / Showers" if code in [51, 53, 55, 61, 63, 65, 80, 81, 82] else "Snowy" if code in [71, 73, 75, 85, 86] else "Thunderstorm" if code in [95, 96, 99] else "Variable"

        return {
            "status": "success",
            "destination": place_name,
            "temperature_celsius": temp_c,
            "temperature_fahrenheit": temp_f,
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "condition": condition,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch live weather: {str(e)}"}


def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "EUR",
) -> dict[str, Any]:
    """Converts a monetary amount between currencies using live exchange rates.
    Ideal for calculating travel budgets, dining expenses, and hotel costs.

    Args:
        amount: The monetary amount to convert (e.g. 150.0).
        from_currency: 3-letter currency code to convert from (e.g. 'USD', 'EUR', 'GBP'). Default 'USD'.
        to_currency: 3-letter currency code to convert to (e.g. 'JPY', 'EUR', 'CAD', 'ISK', 'GBP'). Default 'EUR'.

    Returns:
        A dictionary with original amount, converted amount, exchange rate, and last updated date.
    """
    import json
    import os
    import urllib.request

    base = from_currency.strip().upper()
    target = to_currency.strip().upper()

    # Supports optional API key via EXCHANGE_RATE_API_KEY environment variable if provided
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if api_key:
        api_url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
    else:
        # Free public open tier (no API key required)
        api_url = f"https://open.er-api.com/v6/latest/{base}"

    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "TravelPlanner/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if data.get("result") != "success":
            return {"status": "error", "message": f"Could not retrieve exchange rates for {base}"}

        rates = data.get("rates", {})
        if target not in rates:
            return {"status": "error", "message": f"Currency code '{target}' not supported."}

        rate = rates[target]
        converted_amount = round(amount * rate, 2)

        return {
            "status": "success",
            "from_currency": base,
            "to_currency": target,
            "original_amount": amount,
            "converted_amount": converted_amount,
            "exchange_rate": rate,
            "last_updated": data.get("time_last_update_utc", "latest"),
        }
    except Exception as e:
        return {"status": "error", "message": f"Currency conversion failed: {str(e)}"}


def geocode_address(address: str) -> dict[str, Any]:
    """Uses the Google Maps Geocoding API to turn a street address or landmark into geographic coordinates.

    Args:
        address: The address or place name to geocode (e.g., 'Kinkaku-ji, Kyoto', 'Eiffel Tower, Paris').

    Returns:
        A dictionary containing the formatted address, latitude, and longitude.
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"status": "error", "message": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    try:
        encoded_address = urllib.parse.quote(address.strip())
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "status": "error",
                "message": f"Geocoding failed for '{address}': {data.get('status', 'No results')}",
            }

        first_result = data["results"][0]
        location = first_result["geometry"]["location"]
        return {
            "status": "success",
            "name": address,
            "address": first_result.get("formatted_address"),
            "location": {
                "latitude": location["lat"],
                "longitude": location["lng"],
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Geocoding error: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourist_attraction",
    radius_meters: float = 1500.0,
    max_results: int = 5,
) -> dict[str, Any]:
    """Uses the Google Maps Places API (New) searchNearby REST endpoint to find nearby places of a given type.

    Args:
        latitude: Latitude coordinate of the search center.
        longitude: Longitude coordinate of the search center.
        place_type: Place type to search for (e.g. 'restaurant', 'cafe', 'tourist_attraction', 'museum', 'lodging', 'park').
        radius_meters: Search radius in meters (default: 1500 meters).
        max_results: Max number of places to return (default 5, max 20).

    Returns:
        A list of nearby places with key fields (name, address, location coordinates, place types).
    """
    import json
    import os
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"status": "error", "message": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }
    payload = {
        "includedTypes": [place_type.strip().lower()],
        "maxResultCount": min(max(1, max_results), 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": float(radius_meters),
            }
        },
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        places_raw = data.get("places", [])
        results = []
        for p in places_raw:
            results.append({
                "name": p.get("displayName", {}).get("text", "Unknown"),
                "address": p.get("formattedAddress"),
                "location": p.get("location"),
                "types": p.get("types", []),
            })

        return {
            "status": "success",
            "count": len(results),
            "place_type": place_type,
            "places": results,
        }
    except Exception as e:
        return {"status": "error", "message": f"Nearby places lookup error: {str(e)}"}


from google.adk.tools.tool_context import ToolContext
from google import genai as google_genai
from google.cloud import storage

# Hardcoded bucket name and project ID string
PUBLIC_STORAGE_BUCKET = "bwg3-qwiklabs-gcp-04-b8d4bf5ff8b0"
IMAGE_GEN_MODEL = "gemini-3.1-flash-lite-image"
VIDEO_GEN_MODEL = "gemini-omni-flash-preview"


async def generate_destination_image(
    prompt: str,
    tool_context: ToolContext,
    destination_name: str = "destination",
) -> dict[str, Any]:
    """Generates an illustration/postcard for a travel destination using gemini-3.1-flash-lite-image in the global region.
    The generated image is saved to the Playground Artifacts and uploaded to the public Cloud Storage bucket.

    Args:
        prompt: Detailed visual prompt describing the scene, style, atmosphere, and landmarks.
        tool_context: The ADK ToolContext used to save the artifact into the Playground.
        destination_name: Short name of the destination or landmark for the filename.

    Returns:
        A dictionary with the public HTTPS URL, filename, and generation status.
    """
    import re
    import uuid

    clean_dest = re.sub(r"[^a-zA-Z0-9_-]", "-", destination_name.strip().lower())
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{clean_dest}-{unique_id}.jpg"

    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in global location
        client = google_genai.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT,
            location="global",
        )
        response = client.models.generate_content(
            model=IMAGE_GEN_MODEL,
            contents=prompt,
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"status": "error", "message": "No image data was generated by the model."}

        # 2. Save artifact using tool_context.save_artifact for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(PUBLIC_STORAGE_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{PUBLIC_STORAGE_BUCKET}/{filename}"

        return {
            "status": "success",
            "destination": destination_name,
            "filename": filename,
            "public_url": public_url,
            "mime_type": mime_type,
            "message": f"Successfully generated visual for {destination_name} and uploaded to Cloud Storage.",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate destination image: {str(e)}"}


async def generate_destination_video(
    prompt: str,
    tool_context: ToolContext,
    destination_name: str = "destination",
) -> dict[str, Any]:
    """Generates a short travel video or scenic highlight for a destination or attraction using Google's Omni model (gemini-omni-flash-preview) in the global region.
    The generated video is saved with tool_context.save_artifact to appear in the Playground Artifacts panel, and uploaded directly to the public Cloud Storage bucket.

    Args:
        prompt: Detailed visual prompt describing the scene, motion, atmosphere, camera movement, and landmarks.
        tool_context: The ADK ToolContext used to save the artifact into the Playground.
        destination_name: Short name of the destination or attraction for the filename.

    Returns:
        A dictionary containing the public HTTPS URL, filename, mime_type, and status.
    """
    import base64
    import re
    import uuid

    clean_dest = re.sub(r"[^a-zA-Z0-9_-]", "-", destination_name.strip().lower())
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{clean_dest}-{unique_id}.mp4"

    try:
        # 1. Generate video using gemini-omni-flash-preview via interactions API in global location
        client = google_genai.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT,
            location="global",
        )
        interaction = client.interactions.create(
            model=VIDEO_GEN_MODEL,
            input=prompt,
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(interaction, "output_video") and interaction.output_video:
            ov = interaction.output_video
            if hasattr(ov, "data") and ov.data:
                video_bytes = base64.b64decode(ov.data)
            if hasattr(ov, "mime_type") and ov.mime_type:
                mime_type = ov.mime_type

        # Fallback inspection of steps
        if not video_bytes and hasattr(interaction, "steps"):
            for step in interaction.steps or []:
                for content_item in getattr(step, "content", []) or []:
                    if getattr(content_item, "type", "") == "video" or getattr(content_item, "mime_type", "").startswith("video/"):
                        raw_data = getattr(content_item, "data", None)
                        if raw_data:
                            video_bytes = base64.b64decode(raw_data)
                            mime_type = getattr(content_item, "mime_type", mime_type)
                            break

        if not video_bytes:
            return {"status": "error", "message": "No video data was returned by the Omni model."}

        # 2. Save video artifact using tool_context.save_artifact for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload video bytes to public Cloud Storage bucket without local file writes
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(PUBLIC_STORAGE_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{PUBLIC_STORAGE_BUCKET}/{filename}"

        return {
            "status": "success",
            "destination": destination_name,
            "filename": filename,
            "public_url": public_url,
            "mime_type": mime_type,
            "message": f"Successfully generated short video for {destination_name} and uploaded to Cloud Storage.",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate destination video: {str(e)}"}


from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents.callback_context import CallbackContext

# Agent Engine Code Execution Sandbox & Memory Bank ID (reusing Agent Engine 1147511357642375168)
MEMORY_BANK_ID = "1147511357642375168"
SANDBOX_RESOURCE_NAME = "projects/779526384856/locations/us-central1/reasoningEngines/1147511357642375168/sandboxEnvironments/8668607397746442240"
AGENT_ENGINE_RESOURCE_NAME = "projects/779526384856/locations/us-central1/reasoningEngines/1147511357642375168"


import re
from google.adk.memory.base_memory_service import MemoryEntry

# WRITE: after each turn, send the session to Memory Bank for extraction.
# In addition to automatic session extraction, explicitly detect and guarantee
# that all user allergies, intolerances, and dietary medical restrictions are stored as durable facts.
async def generate_memories_callback(callback_context: CallbackContext):
    session = callback_context._invocation_context.session
    if session and session.events:
        # Check recent user messages for allergies
        allergy_patterns = [
            r"\b(?:allergic to|allergy to|allergies include|have an? allergy to|allergic:?)\s+([^.\n,;!?]+)",
            r"\b(?:intolerant to|intolerance to)\s+([^.\n,;!?]+)",
            r"\b(?:severe|fatal|deadly)?\s*([a-zA-Z\s]+)\s+allergy\b",
            r"\b(?:cannot eat|can't eat|avoid eating|must not eat|must avoid)\s+([^.\n,;!?]+)\b",
        ]
        allergy_facts = []
        for event in session.events:
            if event.content and event.content.role == "user" and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        text = part.text
                        for pat in allergy_patterns:
                            matches = re.findall(pat, text, re.IGNORECASE)
                            for match in matches:
                                cleaned = match.strip() if isinstance(match, str) else "".join(match).strip()
                                if cleaned and len(cleaned) < 80:
                                    allergy_facts.append(f"User allergy / dietary restriction: {cleaned}")

        if allergy_facts:
            try:
                unique_facts = list(dict.fromkeys(allergy_facts))
                memory_entries = [
                    MemoryEntry(content=types.Content(role="user", parts=[types.Part.from_text(text=f)]))
                    for f in unique_facts
                ]
                await callback_context.add_memory(memories=memory_entries)
            except Exception as e:
                logger.warning("Failed to write explicit allergy memory: %s", e)

    # Ingest session into Memory Bank for standard extraction (USER_PERSONAL_INFO, USER_PREFERENCES, etc.)
    await callback_context.add_session_to_memory()
    return None


from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description="""You are an expert Travel Planner AI assistant.
Your goal is to help travelers discover destinations, explore curated travel collections, plan customized day-by-day itineraries, generate destination illustrations/postcards, check live weather, convert trip budgets, find nearby attractions and restaurants, and record travel plans.

CRITICAL MEMORY & ALLERGY SAFETY RULES:
- You remember ALL user allergies (food allergies like peanuts, shellfish, dairy, gluten; environmental allergies; drug/medication allergies; and severe intolerances) from previous conversations and sessions.
- Whenever a user mentions any allergy, intolerance, or dietary medical restriction, immediately acknowledge and confirm that you have permanently remembered it for all current and future trip planning.
- Always check retrieved user memories before recommending restaurants, food experiences, street foods, or culinary itineraries to strictly avoid cross-contamination or dishes containing the user's allergens.
- In addition to allergies, you remember the traveler's stated preferences, travel styles, past visits, and facts from previous conversations and use them to personalize your recommendations.

You also have a secure Python Code Execution sandbox environment (`code_executor`). Whenever the user needs complex calculations (such as cost breakdown, currency splits, statistical analysis, or data manipulation), write and execute Python code in the sandbox to calculate the exact results.

You have access to tools for destinations, imagery, weather, budgets, places, memory, and itineraries:
- `PreloadMemoryTool` automatically retrieves long-term traveler preferences, allergies, and facts from your Memory Bank at turn start.
- Use `generate_destination_image` to create custom postcards, landscape illustrations, and travel visuals for destinations or itineraries.
- Use `generate_destination_video` to generate short video highlights for a destination, landmark, or scenic attraction using Google's Omni model.
- Use `geocode_address` to find exact coordinates and address for any landmark, city, or point of interest.
- Use `find_nearby_places` to discover nearby restaurants, cafes, museums, attractions, or hotels around coordinates.
- Use `convert_currency` to calculate currency exchange and local trip costs (e.g. converting daily USD budget to JPY, EUR, CAD, ISK).
- Use `get_live_destination_weather` to check real-time weather and temperature before planning or packing.
- Use `list_destinations` or `search_destinations` to find recommendations, attraction highlights, best seasons, and daily budgets from the catalog.
- Use `save_destination` if the user wants to add or update a destination in the catalog.
- Use `save_traveler_itinerary` when the traveler wants to save a planned itinerary for future reference.
- Use `get_current_time` to check local time in destination cities.

Always provide helpful, well-structured travel suggestions with actionable advice, estimated budgets, and duration recommendations.""",
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        generate_destination_image,
        generate_destination_video,
        geocode_address,
        find_nearby_places,
        get_live_destination_weather,
        convert_currency,
        list_destinations,
        search_destinations,
        save_destination,
        save_traveler_itinerary,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)





