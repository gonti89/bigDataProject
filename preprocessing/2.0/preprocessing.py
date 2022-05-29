import argparse
import pyspark.sql.functions as F
from pyspark.sql import SparkSession


def initArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("kafkaServer")
    parser.add_argument("kafkaPort")
    parser.add_argument("inKafkaTopic")
    parser.add_argument("outKafkaTopic")

    return parser.parse_args()


def initSpark():
    spark = (
        SparkSession
        .builder
        .master("local[*]")
        .appName("test Count")
        .config('spark.jars.packages', "org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1")
        .getOrCreate()
    )
    return spark


def main():
    args = initArgs()
    bootstrap_servers = f'{args.kafkaServer}:{args.kafkaPort}'
    inTopic = args.inKafkaTopic
    outTopic = args.outKafkaTopic

    eventSchema = """
           time INTEGER, 
           cookieID STRING, 
           userAgent STRING,  
           url STRING, 
           referer STRING, 
           ip STRING
           """

    with initSpark() as ss:
        kafka_raw_stream = (ss
                            .readStream
                            .format('kafka')
                            .option('kafka.bootstrap.servers', bootstrap_servers)
                            .option('subscribe', inTopic)
                            .load()
                            )
        kafka_stream = (
            kafka_raw_stream
                .selectExpr('CAST(key as String)', 'CAST(value as String)')
        )
        eventsPreprocessed = (
            kafka_stream
                .withColumn("data", F.from_json("value", eventSchema))
                .selectExpr('key', 'data.*')
                .withColumn('ipHash', F.hash("ip"))
                .withColumn('splitIp', F.split("ip", "\."))
                .withColumn('shortIp', F.concat_ws(".", F.slice("splitIp", start=1, length=3)))
                .drop("ip", "splitIp")
        )

        baseQuery = (
            eventsPreprocessed
                .selectExpr("to_json(struct(*)) AS value")
                .writeStream
                .format('kafka')
                .option('topic', outTopic)
                .option("kafka.bootstrap.servers", bootstrap_servers)
                .trigger(processingTime='1 second')
                .option("checkpointLocation", "./chkptPreprocess")
                .start()
        )

        ss.streams.awaitAnyTermination()


if __name__ == '__main__':
    main()
