from time import sleep
from datetime import datetime
import json
import random
import argparse
from faker import Faker
from kafka import KafkaProducer

parser = argparse.ArgumentParser(description="Kafka data generator")
parser.add_argument("kafka", help="address:port of one of kafka servers")
parser.add_argument("kafkaPort")
parser.add_argument("kafkaTopic")
args = parser.parse_args()

print(args.kafka, args.kafkaTopic, args.kafkaPort)

fake = Faker()

producer = KafkaProducer(bootstrap_servers=[f"{args.kafka}:{args.kafkaPort}"],
                         value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                         api_version=(2, 6, 0))

print("Producer started")

try:
    while True:
        message = {"time": int(datetime.utcnow().timestamp()), "age": random.randint(0, 100), 
                   "name": fake.name(), "address": fake.address().replace("\n", " "), "zipcode": fake.zipcode(),
                   "action": random.choice("abcdef")}
        producer.send(args.kafkaTopic, value=message)
        sleep(1)
except KeyboardInterrupt:
    producer.close()
