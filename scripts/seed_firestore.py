"""Seed script for Firestore spells collection."""
import google.auth
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-f77911216b85"

INITIAL_SPELLS = [
    {
        "id": "fireball",
        "name": "Fireball",
        "level": 3,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "150 feet",
        "damage_or_effect": "8d6 fire damage in a 20-foot radius sphere (Dex save for half)",
        "description": "A bright streak flashes from your pointing finger to a point you choose within range and blossoms into an explosion of flame.",
    },
    {
        "id": "healing-word",
        "name": "Healing Word",
        "level": 1,
        "school": "Evocation",
        "casting_time": "1 bonus action",
        "range": "60 feet",
        "damage_or_effect": "Restores 1d4 + Spellcasting Modifier HP",
        "description": "A creature of your choice that you can see within range regains hit points.",
    },
    {
        "id": "shield",
        "name": "Shield",
        "level": 1,
        "school": "Abjuration",
        "casting_time": "1 reaction",
        "range": "Self",
        "damage_or_effect": "+5 bonus to AC until start of your next turn",
        "description": "An invisible barrier of magical force appears and protects you.",
    },
    {
        "id": "misty-step",
        "name": "Misty Step",
        "level": 2,
        "school": "Conjuration",
        "casting_time": "1 bonus action",
        "range": "Self",
        "damage_or_effect": "Teleport up to 30 feet to an unoccupied space you can see",
        "description": "Briefly surrounded by silvery mist, you teleport up to 30 feet to an unoccupied space.",
    },
    {
        "id": "lightning-bolt",
        "name": "Lightning Bolt",
        "level": 3,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "Self (100-foot line)",
        "damage_or_effect": "8d6 lightning damage in a 100-foot line (Dex save for half)",
        "description": "A stroke of lightning forming a line 100 feet long and 5 feet wide blasts out from you.",
    },
]

def seed_firestore():
    creds, _ = google.auth.default()
    db = firestore.Client(project=PROJECT_ID, credentials=creds)
    collection_ref = db.collection("spells")
    print(f"Seeding 'spells' collection in Firestore (Project: {PROJECT_ID})...")
    for spell in INITIAL_SPELLS:
        doc_ref = collection_ref.document(spell["id"])
        doc_ref.set(spell)
        print(f"  - Seeded spell: {spell['name']} (ID: {spell['id']})")
    print("Firestore seeding complete!")

if __name__ == "__main__":
    seed_firestore()
