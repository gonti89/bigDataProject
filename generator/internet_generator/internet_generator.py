import argparse
import json

from datetime import datetime
from collections import OrderedDict
from time import sleep

from faker.providers import DynamicProvider
from faker import Faker
from kafka import KafkaProducer


def generateUniqueCookie(count=100):
    fake = Faker()
    return [fake.uuid4(cast_to=int) for _ in range(count)]


def generateUserAgent(count=100):
    fake = Faker()
    return [fake.user_agent() for _ in range(count)]


def initArgs():
    parser = argparse.ArgumentParser(description="Kafka data generator")
    parser.add_argument("kafka", help="address:port of one of kafka servers")
    parser.add_argument("kafkaPort")
    parser.add_argument("kafkaTopic")
    parser.add_argument("cookiesNumber", type=int)
    parser.add_argument("domainName", type=str)
    return parser.parse_args()


def main():
    args = initArgs()
    idCount = args.cookiesNumber
    kafka_bootstrap_servers = [f"{args.kafka}:{args.kafkaPort}"]
    domain = args.domainName
    urlParamsOptions = OrderedDict([("", 0.8), ("?testVersion=a", 0.10), ("?testVersion=b", 0.10), ])
    refOptions = OrderedDict([("", 0.3), ("facebook.com", 0.10), ("google.com", 0.10), (domain, 0.50)])

    #define new provider to assure that cookies have the same userAgent all the time
    cookie_ua_provider = DynamicProvider(
        provider_name="cookie_ua",
        elements=[(x, y) for x, y in zip(generateUniqueCookie(idCount), generateUserAgent(idCount))]
    )
    fake = Faker()
    fake.add_provider(cookie_ua_provider)

    producer = KafkaProducer(bootstrap_servers=kafka_bootstrap_servers,
                            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                            api_version=(2, 6, 0))

    print("Producer started")

    try:
        while True:
            cookieID, ua = fake.cookie_ua()
            uri = fake.uri_path()
            urlParams = fake.random_element(elements=urlParamsOptions)
            url = f"{domain}/{uri}{urlParams}"

            message = {
                    "time": int(datetime.utcnow().timestamp()),
                    "cookieID": cookieID,
                    "userAgent": ua,
                    "url": url,
                    "referer": fake.random_element(elements=refOptions),
                    "ip": fake.ipv4()
                    }
            producer.send(args.kafkaTopic, value=message)
            sleep(1)
    except KeyboardInterrupt:
        pass
        producer.close()


if __name__ == '__main__':
    main()
