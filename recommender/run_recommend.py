import os, json, time
from collections import deque
from datetime import datetime

from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI, RateLimitError

# ─── Configuration from ENV ────────────────────────────────────────────────────
BOOTSTRAP    = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
SRC_TOPIC    = os.getenv("SOURCE_TOPIC", "listening_events_enriched")
DEST_TOPIC   = os.getenv("DEST_TOPIC", "song_recommendations")
BUF_SIZE     = int(os.getenv("RECO_HISTORY_SIZE", "10"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")    # must be set via .env or compose

# ─── Kafka & OpenAI Clients ────────────────────────────────────────────────────
consumer = KafkaConsumer(
    SRC_TOPIC,
    bootstrap_servers=BOOTSTRAP.split(","),
    value_deserializer=lambda v: json.loads(v.decode()),
    auto_offset_reset="earliest",
    enable_auto_commit=True,
)

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP.split(","),
    value_serializer=lambda v: json.dumps(v).encode(),
)

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Circular buffer for history ───────────────────────────────────────────────
history = deque(maxlen=BUF_SIZE)

print(f"▶ Listening for enriched events… (buffer={BUF_SIZE})")

for msg in consumer:
    evt = msg.value
    title = evt["metadata"]["title"]
    artist = evt["metadata"]["artist_name"]
    history.append(f"{title} by {artist}")
    print(f"📝 Buffered: {title}")

    # only call OpenAI once buffer is full
    if len(history) >= BUF_SIZE:
        prompt = (
            "I recently listened to the following songs:\n\n"
            + "\n".join(f"{i+1}. {s}" for i, s in enumerate(history))
            + "\n\nPlease recommend 3 more songs I might like, with explanation."
        )

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
        except RateLimitError:
            # back off on rate limits
            time.sleep(1)
            continue

        recs = resp.choices[0].message.content.strip()
        print("\n🎵 Recommendations based on your recent history:\n", recs, "\n")

        # publish the recommendations back into Kafka
        producer.send(
            DEST_TOPIC,
            value={
                "recommendations": recs,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        producer.flush()
