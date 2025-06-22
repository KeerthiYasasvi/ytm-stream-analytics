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
YouTube Music Simulator
↓
Kafka
(listening_events → listening_events_enriched → song_recommendations)
↓
Spark Streaming
(writes Parquet)
↓
Recommender Service (OpenAI ChatGPT)
↓
UI (Flask + SSE)

```

---
