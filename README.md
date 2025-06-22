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

---


1. **Simulator**: Polls your YouTube Music history via `ytmusicapi`, publishes raw listen events to Kafka.  
2. **Enricher**: A light container that reads raw events, adds metadata (duration, release date), writes to `listening_events_enriched`.  
3. **Spark Streaming**: Reads the enriched topic, writes every event to Parquet for analytics.  
4. **Recommender**: Reads enriched events in batches, calls OpenAI ChatGPT for 3-song recommendations based on recent history, publishes to Kafka.  
5. **UI**: Flask app that backfills & tails your history and recommendation topics, shows recent tracks & live recommendations in browser.

---

## Prerequisites

- **Docker** & **docker-compose** (v1.27+ recommended)  
- A valid **YouTube Music** `browser.json` auth file for `ytmusicapi`  
- An **OpenAI API Key** with quota to call ChatGPT models  

---

## Setup & Configuration

1. **Clone** this repository:  
   ```bash
   git clone https://github.com/your-username/ytm-stream-analytics.git
   cd ytm-stream-analytics

2. **Create** a .env in the project root:
   ### Kafka
   KAFKA_BROKER_ADDRESS=kafka
   KAFKA_BROKER_PORT=9092

   ### OpenAI
   OPENAI_API_KEY=sk-your-key-here

3. **Place** your YouTube Music auth:
   simulator/browser.json
