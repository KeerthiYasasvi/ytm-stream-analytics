"""
create_topic.py

Simple CLI to auto-create the raw Kafka topic if it doesn’t already exist.
"""
import os
from kafka.admin import KafkaAdminClient, NewTopic

def create_topic(topic_name="listening_events"):
    admin = KafkaAdminClient(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
    admin.create_topics([topic])
    print(f"✅ Created topic {topic_name}")

if __name__ == "__main__":
    # You can override the topic name by passing it as an arg, if you like.
    create_topic()
