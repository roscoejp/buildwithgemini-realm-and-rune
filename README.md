# Realm & Rune RPG Companion

An AI-powered tabletop fantasy RPG companion built with Google ADK (Agent Development Kit), Vertex AI Gemini, and Google Cloud services. Realm & Rune assists Dungeon Masters and players with monster stat lookups, spell management, virtual dice rolling, item artwork generation, cinematic video showcases, and campaign location inspirations.

![Realm & Rune Demo](demo.gif)

---

## 🔮 Implemented Capabilities & Google Cloud Integrations

Realm & Rune is powered by the **Google Agent Development Kit (ADK)** and leverages the following Google Cloud services and tools:

* **Vertex AI Memory Bank (`VertexAiMemoryBankService`)**: Automatically persists long-term campaign details, party member facts, and user preferences across sessions.
* **Google Cloud Firestore (`google.cloud.firestore`)**: Stores and queries D&D 5e spell records (`get_spell`, `search_spells`, `add_spell`) and monster stat entries.
* **Vertex AI Image Generation (Imagen)**: Uses `gemini-3.1-flash-lite-image` in global region to generate fantasy creature, spell, and item artwork on demand.
* **Vertex AI Omni Video Showcase (`gemini-omni-flash-preview`)**: Generates short cinematic video showcases for magical items and artifacts in global region.
* **Google Cloud Storage (GCS)**: Automatically uploads generated item artwork, spell boomerang GIFs, and video showcases to a public Cloud Storage bucket.
* **A2UI Rich UI Catalog (`a2ui` v0.8 Basic Catalog)**: Emits structured UI card payloads (`application/json+a2ui`) that render responsive monster stat blocks, spell cards, and item displays directly in the chat UI.
* **Google Maps Geocoding & Places API**: Translates real-world addresses into geographic coordinates (`geocode_address`) and finds nearby location inspirations (`find_nearby_places`) for campaign map design.
* **Virtual Dice Roller (`roll_dice`)**: Parses standard tabletop dice notation (`1d20`, `4d6+3`, `8d6`) and returns individual roll breakdowns with total sums.
* **Secure Code Sandbox (`AgentEngineSandboxCodeExecutor`)**: Executes Python code snippets safely inside an isolated Agent Engine sandbox environment.

---

## 🛠️ Repository Structure

```
realm-and-rune/
├── app/
│   ├── agent.py          # Root ADK agent configuration, memory service, & system instructions
│   ├── tools.py          # Tool definitions (Firestore, Imagen, Omni Video, Dice, Maps APIs)
│   └── a2ui_utils.py     # A2UI model callback for rendering rich UI cards
├── frontend/
│   ├── main.py           # FastAPI proxy forwarding browser chats to Agent Runtime via A2A
│   ├── Dockerfile        # Container build definition for Cloud Run deployment
│   └── static/
│       ├── index.html    # Responsive web chat interface with A2UI renderer & dark mode toggle
│       ├── logo.png      # Minimalist RPG shield logo
│       └── favicon.png   # Application browser favicon
├── agents-cli-manifest.yaml # Agent Deployment manifest (ACLI v1.7.0)
├── demo.gif              # Loop demonstration recording of the live agent
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## 🚀 Setup & Execution Instructions

### 1. Prerequisites

* Python 3.10+
* Google Cloud Platform (GCP) Project with Vertex AI, Firestore, and Cloud Storage APIs enabled
* Google Cloud SDK (`gcloud`) and `uv` CLI installed

### 2. Environment Configuration

Copy `.env.example` to `.env` and set your API keys:

```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

### 3. Local Development

Install dependencies and start the agent locally using the ADK Playground or local FastAPI proxy:

#### Option A: ADK Playground
```bash
agents-cli playground
```

#### Option B: Local Web Proxy & Chat UI
```bash
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"
export AGENT_DIRECTORY="app"
python frontend/main.py
```
Open your browser to the local server port printed in the terminal (default port 8080).

---

## ☁️ Deployment

### Deploy Agent to Agent Runtime

To deploy or update the agent on Vertex AI Agent Engine:

```bash
agents-cli deploy \
  --project YOUR_PROJECT_ID \
  --no-confirm-project \
  --service-name my-sample-agent \
  --update-env-vars GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

### Deploy Frontend to Cloud Run

To build and deploy the web chat frontend to Google Cloud Run:

```bash
cd frontend
gcloud run deploy realm-and-rune-frontend \
  --source . \
  --region us-central1 \
  --quiet
```
