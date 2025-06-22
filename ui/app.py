"""
ui/app.py

Flask dashboard for recent YTM listens and ChatGPT song recs.
"""
import logging, json, threading, os
from collections import deque
from flask import Flask, jsonify, render_template, Response
from kafka import KafkaConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [UI] %(message)s")

app = Flask(__name__)

HISTORY = deque(maxlen=100)
RECS    = deque(maxlen=10)

def history_reader():
    topic = os.getenv("HISTORY_TOPIC", "listening_events")
    brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    logging.info(f"[history_reader] subscribing to {topic} on {brokers}")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=brokers.split(","),
        group_id="ui-history",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    for msg in consumer:
        HISTORY.append(msg.value)

def recs_reader():
    topic = os.getenv("RECOMMENDATIONS_TOPIC", "song_recommendations")
    brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    logging.info(f"[recs_reader] subscribing to {topic} on {brokers}")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=brokers.split(","),
        group_id="ui-recs",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    for msg in consumer:
        rec = msg.value.get("recommendations")
        if rec:
            RECS.append(rec)

# start background threads before any request
threading.Thread(target=history_reader, daemon=True).start()
threading.Thread(target=recs_reader,    daemon=True).start()

@app.route("/")
def index():
    latest = RECS[-1] if RECS else None
    return render_template("index.html", latest_rec=latest)

@app.route("/api/history")
def api_history():
    """
    Return the 20 most recent listens (newest first).
    """
    recent = list(HISTORY)[-20:][::-1]
    return jsonify(recent)

@app.route("/api/recommendations")
def api_recs():
    """
    SSE endpoint for real-time recommendations.
    """
    def event_stream():
        last = 0
        while True:
            if len(RECS) > last:
                rec = RECS[last]
                last += 1
                yield f"data: {json.dumps(rec)}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
