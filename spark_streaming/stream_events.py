from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, TimestampType
)

# 1) JSON schema
schema = StructType([
    StructField("user_id", StringType()),
    StructField("track_id", StringType()),
    StructField("artist_id", StringType()),
    StructField("timestamp", StringType()),
    StructField("duration_ms", LongType()),
    StructField("metadata", StructType([
        StructField("title", StringType()),
        StructField("album", StructType([
            StructField("name", StringType()),
            StructField("id", StringType())
        ])),
        StructField("artist_name", StringType()),
        # enriched
        StructField("release_date", StringType())
    ]))
])

spark = (
    SparkSession.builder
      .appName("ytm-listen-stream")
      .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# 2) Read from Kafka enriched topic
kafkaDF = (
    spark.readStream
         .format("kafka")
         .option("kafka.bootstrap.servers", "kafka:9092")
         .option("subscribe", "listening_events_enriched")
         .option("startingOffsets", "earliest")
         .option("failOnDataLoss", "false")
         .load()
)

# 3) Parse JSON
events = (
    kafkaDF.selectExpr("CAST(value AS STRING) AS json")
           .select(from_json(col("json"), schema).alias("evt"))
           .select(
               col("evt.user_id"),
               col("evt.track_id"),
               col("evt.artist_id"),
               col("evt.timestamp").cast(TimestampType()).alias("ts"),
               col("evt.duration_ms"),
               col("evt.metadata.title").alias("title"),
               col("evt.metadata.artist_name").alias("artist_name"),
               col("evt.metadata.release_date").alias("release_date")
           )
)

# 4) Write to Parquet
(
    events.writeStream
          .format("parquet")
          .option("path", "/opt/spark/output")
          .option("checkpointLocation", "/opt/spark/checkpoints")
          .outputMode("append")
          .start()
          .awaitTermination()
)
