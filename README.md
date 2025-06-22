# yt-music-simulator

# YouTube Music → Kafka → Spark → ChatGPT Pipeline

A real-time data pipeline that reads your YouTube Music listening history, streams it through Kafka, enriches it, processes it in Spark, generates personalized song recommendations via the OpenAI API, and exposes everything in a simple browser UI.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)  
2. [Prerequisites](#prerequisites)  
3. [Setup & Configuration](#setup--configuration)  
4. [Running the Pipeline](#running-the-pipeline)  
5. [Usage](#usage)  
6. [Directory Structure](#directory-structure)  
7. [Customization & Extending](#customization--extending)  
8. [Troubleshooting](#troubleshooting)  
9. [Future Improvements](#future-improvements)  
10. [License & Acknowledgments](#license--acknowledgments)  

---

## Architecture Overview

```text
YouTube Music Simulator ──▶ Kafka (listening_events → listening_events_enriched → song_recommendations) ──▶ Spark Streaming (writes Parquet) ──▶ Recommender Service (OpenAI ChatGPT) ──▶ UI (Flask + SSE)

```


1. **Simulator**: Polls your YouTube Music history via `ytmusicapi`, publishes raw listen events to Kafka.  
2. **Enricher**: A light container that reads raw events, adds metadata (duration, release date), writes to `listening_events_enriched`.  
3. **Spark Streaming**: Reads the enriched topic, writes every event to Parquet for analytics.  
4. **Recommender**: Reads enriched events in batches, calls OpenAI ChatGPT for 3-song recommendations based on recent history, publishes to Kafka.  
5. **UI**: Flask app that backfills & tails your history and recommendation topics, shows recent tracks & live recommendations in browser.

## Prerequisites

- **Docker** & **docker-compose** (v1.27+ recommended)  
- A valid **YouTube Music** `browser.json` auth file for `ytmusicapi`  
- An **OpenAI API Key** with quota to call ChatGPT models  

## Setup & Configuration

1. **Clone** this repository:  
   ```bash
   git clone https://github.com/your-username/ytm-stream-analytics.git
   cd ytm-stream-analytics

2. **Create** a .env in the project root:
   
   *(Kafka)*
   
   KAFKA_BROKER_ADDRESS=kafka
   KAFKA_BROKER_PORT=9092

   *(OpenAI)*
   
   OPENAI_API_KEY=sk-your-key-here

3. **Generate** your YouTube Music auth file:
   
   ```bash
   # In a browser session, follow the ytmusicapi guide:
   #   https://github.com/sigma67/ytmusicapi#setup
   # or simply:
   python simulator/setup_browser.py

## Running the Pipeline

**Build and start** all services:

```
docker-compose up --build
```

You should see logs indicating:

- Simulator is polling and publishing new events
- Kafka topics being created
- Spark writing Parquet files under spark_output/
- Recommender buffering events and calling ChatGPT
- UI serving on http://localhost:5000

## Usage

- **Browser UI:**
  Open http://localhost:5000 to view:
     - Recent Tracks (last 20 listens)
     - Latest Recommendation (batch of 3 songs)
     - Live Recommendations as new batches arrive

 - **Kafka CLI:**

   ```text

   # Raw events
   kafka-console-consumer --bootstrap-server localhost:9092 \
     --topic listening_events --from-beginning --max-messages 5

   # Enriched events
   kafka-console-consumer --bootstrap-server localhost:9092 \
     --topic listening_events_enriched --from-beginning --max-messages 5
   
   # Recommendations
   kafka-console-consumer --bootstrap-server localhost:9092 \
     --topic song_recommendations --from-beginning --max-messages 5

   ```

## Directory Structure

```text

ytm-stream-analytics/
├── .env
├── docker-compose.yml
├── Dockerfile.enricher       # Enricher service
├── README.md
│
├── simulator/                # YouTube Music simulator + topic creation
│   ├── browser.json
│   ├── create_topic.py
│   ├── Dockerfile.simulator
│   ├── requirements.txt
│   └── simulator.py
│
├── spark_streaming/          # Spark streaming job (writes Parquet)
│   ├── schema.py
│   └── stream_events.py
│
├── recommender/              # ChatGPT recommender service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run_recommend.py
│
└── ui/                       # Flask UI & SSE
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py
    └── templates/index.html

```

## Customization & Extending

 - **Buffer size** for recommendations: adjust RECO_HISTORY_SIZE in .env or docker-compose.yml.
 - **Model**: change model="gpt-4o-mini" in run_recommend.py.
 - **Kafka topics**: override SOURCE_TOPIC, DEST_TOPIC, HISTORY_TOPIC, RECOMMENDATIONS_TOPIC as needed.
 - **Spark output**: modify Parquet path or add additional aggregations in stream_events.py.

## Troubleshooting

 - **Kafka topic not found**: make sure KAFKA_CREATE_TOPICS env in docker-compose.yml includes all three topics.
 - **OpenAI 429 rate limit**: reduce consumption rate or add retry logic.
 - **YouTube Music auth errors**: regenerate browser.json via setup_browser.py steps in simulator/.
 - **Spark “NoClassDefFoundError”**: ensure the Kafka connector version (spark-sql-kafka-0-10_2.12) matches your Spark Scala version.

## Future Improvements

 - **Feedback loop**: let UI capture which recommendations you “like” and refine future prompts.
 - **Dashboard analytics**: use stored Parquet in a BI tool (e.g. Superset, Grafana).
 - **Authentication**: secure the UI with basic auth.
 - **Deployment**: swap Flask dev server for Gunicorn / Nginx.
