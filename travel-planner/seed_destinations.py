"""Seeds initial destinations data into Firestore for the Travel Planner agent."""

from google.cloud import firestore

# Pin the project ID explicitly as a string:
FIRESTORE_PROJECT = "qwiklabs-gcp-04-b8d4bf5ff8b0"

DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "city": "Kyoto",
        "country": "Japan",
        "category": "Culture & Heritage",
        "tags": ["temples", "gardens", "zen", "cuisine", "historic"],
        "recommended_days": 4,
        "estimated_budget_per_day_usd": 150,
        "best_season": "Spring (Cherry Blossoms) or Autumn (Foliage)",
        "summary": "Ancient imperial capital known for thousands of classical Buddhist temples, serene rock gardens, and traditional wooden houses.",
        "highlights": [
            "Fushimi Inari Shrine torii path",
            "Arashiyama Bamboo Grove",
            "Kinkaku-ji (Golden Pavilion)",
            "Gion Geisha district evening walk"
        ],
        "image_prompt": "A serene watercolor and ink illustration of Kyoto's Golden Pavilion reflecting in still water surrounded by autumn maple trees."
    },
    {
        "id": "paris-france",
        "city": "Paris",
        "country": "France",
        "category": "Art & Romance",
        "tags": ["art", "museums", "cafes", "architecture", "romantic"],
        "recommended_days": 5,
        "estimated_budget_per_day_usd": 220,
        "best_season": "Spring or Early Autumn",
        "summary": "Global hub for art, fashion, gastronomy, and culture with iconic Haussmann architecture and cobblestone cafe-lined streets.",
        "highlights": [
            "Louvre Museum & Musée d'Orsay masterpieces",
            "Sunset at the Eiffel Tower & Trocadéro",
            "Montmartre and Sacré-Cœur artists square",
            "Seine riverboat cruise and bakery crawling"
        ],
        "image_prompt": "A warm vintage travel poster style illustration of a charming Parisian bistro patio with the Eiffel Tower in the soft pastel background."
    },
    {
        "id": "banff-canada",
        "city": "Banff",
        "country": "Canada",
        "category": "Nature & Adventure",
        "tags": ["mountains", "hiking", "lakes", "wildlife", "outdoors"],
        "recommended_days": 4,
        "estimated_budget_per_day_usd": 180,
        "best_season": "Summer for hiking, Winter for skiing",
        "summary": "Glacier-fed turquoise lakes surrounded by the majestic peaks of the Canadian Rockies in Alberta's oldest national park.",
        "highlights": [
            "Canoeing on Lake Louise and Moraine Lake",
            "Hiking the Plain of Six Glaciers Teahouse trail",
            "Banff Upper Hot Springs relaxation",
            "Scenic drive on Icefields Parkway"
        ],
        "image_prompt": "A majestic panoramic illustration of turquoise Lake Louise framed by towering snow-capped Rocky Mountain peaks and pine trees."
    },
    {
        "id": "reykjavik-iceland",
        "city": "Reykjavik",
        "country": "Iceland",
        "category": "Scenic & Geothermal",
        "tags": ["waterfalls", "northern lights", "volcanoes", "geothermal", "nature"],
        "recommended_days": 5,
        "estimated_budget_per_day_usd": 250,
        "best_season": "Autumn/Winter for Aurora, Summer for Midnight Sun",
        "summary": "Land of fire and ice with dramatic volcanic landscapes, cascading waterfalls, black sand beaches, and steaming geothermal lagoons.",
        "highlights": [
            "Golden Circle route (Geysir, Gullfoss, Thingvellir)",
            "Blue Lagoon geothermal soak",
            "Chasing the Aurora Borealis in dark skies",
            "Black sand beach and basalt columns in Vik"
        ],
        "image_prompt": "An atmospheric atmospheric illustration of Iceland's green aurora borealis dancing over a dramatic waterfall and black volcanic moss."
    },
    {
        "id": "oia-santorini",
        "city": "Santorini",
        "country": "Greece",
        "category": "Coast & Relaxation",
        "tags": ["sunset", "islands", "beaches", "views", "seafood"],
        "recommended_days": 3,
        "estimated_budget_per_day_usd": 210,
        "best_season": "Late Spring to Early Autumn (May - October)",
        "summary": "Volcanic island in the Cyclades renowned for dramatic cliffside whitewashed cubiform villages overlooking the Aegean caldera.",
        "highlights": [
            "Oia caldera sunset viewing",
            "Hiking the coastal trail from Fira to Oia",
            "Catamaran cruise around volcanic hot springs",
            "Akrotiri prehistoric ruins & red beach"
        ],
        "image_prompt": "A vibrant sun-drenched illustration of whitewashed blue-domed Santorini houses cascading down the cliff overlooking the deep blue caldera."
    }
]


def seed_firestore():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT}...")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    collection_ref = db.collection("destinations")

    count = 0
    for dest in DESTINATIONS:
        doc_id = dest["id"]
        collection_ref.document(doc_id).set(dest)
        print(f"  ✓ Added destination: {dest['city']} ({dest['country']}) -> destinations/{doc_id}")
        count += 1

    print(f"\nSuccessfully seeded {count} destinations to Firestore collection 'destinations'.")


if __name__ == "__main__":
    seed_firestore()
