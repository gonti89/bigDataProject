import argparse
import pyspark.sql.functions as F
from pyspark.sql.types import ArrayType, StringType, MapType, StructType, StructField
from pyspark.sql import SparkSession
from user_agents import parse


def initArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("kafkaServer")
    parser.add_argument("kafkaPort")
    parser.add_argument("inKafkaTopic")
    parser.add_argument("outKafkaTopicDeco")
    parser.add_argument("outKafkaTopicSession")
    parser.add_argument("user_session_max_gap_minutes", type=int)

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


@F.udf(returnType=StructType(
    [
        StructField("deviceType", StringType()),
        StructField("os", StringType()),
        StructField("browser", StringType()),
    ]))
def parseUserAgent(ua_string):
    if ua_string is None:
        ua_string = ""

    parsed_string = parse(ua_string)

    if parsed_string.is_pc:
        deviceType = "pc"
    elif parsed_string.is_mobile:
        deviceType = "mobile"
    elif parsed_string.is_tablet:
        deviceType = "tablet"
    else:
        deviceType = "other"

    output = {
        "deviceType": deviceType,
        "os": parsed_string.os.family,
        "browser": parsed_string.browser.family
    }
    return output


def main():
    args = initArgs()

    bootstrap_servers = f'{args.kafkaServer}:{args.kafkaPort}'
    inTopic = args.inKafkaTopic
    outDecoTopic = args.outKafkaTopicDeco
    outSessionTopic = args.outKafkaTopicSession

    baseEventsProcessingTime = '60 seconds'
    sessionProcessingTime = '1 minute'

    windowPeriodSeconds = args.user_session_max_gap_minutes * 60  # transform minutes to seconds
    windowSessionTime = f"{windowPeriodSeconds} seconds"

    eventSchema = """
        time TIMESTAMP, 
        cookieID STRING, 
        userAgent STRING,  
        url STRING, 
        referer STRING, 
        ipHash INTEGER,
        shortIp STRING
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
        eventsDecorated = (
            kafka_stream
                .withColumn("data", F.from_json("value", eventSchema))
                .selectExpr('key', 'data.*')
                .withColumn('parsedUa', parseUserAgent("userAgent"))
                .selectExpr('*', 'parsedUa.*')
                .drop("parsedUA")
        )
        session = (
            eventsDecorated
                .withColumn("urlNoParams", F.regexp_extract('url', r'[^?]*', 0))
                .withWatermark("time", "1 minute")
                .groupBy("cookieID", "deviceType", "os", "browser", F.session_window("time", windowSessionTime))
                .agg(F.count("*").alias('events'),
                     F.collect_set("urlNoParams").alias("uniqueUrls"))
                .withColumn("sessionStart", F.col("session_window").start.cast("int"))
                .withColumn("sessionEnd", F.col("session_window").end.cast("int"))
                .withColumn("sessionDuration", F.col("sessionEnd") - F.col("sessionStart") - F.lit(windowPeriodSeconds))
                .withColumn("sessionUniqueUrlsCount", F.size("uniqueUrls"))

        )

        baseQuery = (
            eventsDecorated
                .withColumn("time", F.col("time").cast('int'))
                .selectExpr("to_json(struct(*)) AS value")
                .writeStream
                .format('kafka')
                .option('topic', outDecoTopic)
                .option("kafka.bootstrap.servers", bootstrap_servers)
                .trigger(processingTime=baseEventsProcessingTime)
                .option("checkpointLocation", "./chkptDeco")
                .start()
        )

        sessionQuery = (
            session
                .drop("session_window", "uniqueUrls")
                .selectExpr("to_json(struct(*)) AS value")
                .writeStream
                .format('kafka')
                .option('topic', outSessionTopic)
                .option("kafka.bootstrap.servers", bootstrap_servers)
                .trigger(processingTime=sessionProcessingTime)
                .option("checkpointLocation", "./chkpt")
                .start()
        )
        ss.streams.awaitAnyTermination()


if __name__ == '__main__':
    main()
