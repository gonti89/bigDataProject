import argparse
import json
import random

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


def getCookieUa(elemCount=10):
    cookies = generateUniqueCookie(elemCount)
    ua = generateUserAgent(elemCount)
    activityLevel = [random.random() for _ in range(elemCount)]
    cookie_ua_elements = [(x, y, z) for x, y, z in zip(cookies, ua, activityLevel)]
    return cookie_ua_elements


class CookieUaProvider(DynamicProvider):
    def __init__(self, provider_name, elements=None, generator=None, initElemCount=10):
        super().__init__(provider_name, elements, generator)

        if elements is None:
            allElements = getCookieUa(elemCount=initElemCount * 10)
            self.elements = self.random_sample(elements=allElements, length=initElemCount)

        else:
            assert len(elements) > 0
            allElements = None
            self.elements = elements

        self.allElements = allElements

    def replace_random_elements(self, replaceRate=0.2):
        assert replaceRate < 1
        assert replaceRate > 0

        currentCount = len(self.elements)

        length = int((1 - replaceRate) * currentCount)
        notRemovedElements = self.random_sample(elements=self.elements, length=length)

        newCount = currentCount - length
        newElements = self.random_sample(elements=self.allElements, length=newCount)

        self.elements = notRemovedElements + newElements  # elems are initilized in super class
        print("replacedCookies")


def initArgs():
    parser = argparse.ArgumentParser(description="Kafka data generator")
    parser.add_argument("kafka", help="address:port of one of kafka servers")
    parser.add_argument("kafkaPort")
    parser.add_argument("kafkaTopic")
    parser.add_argument("cookiesNumber", type=int)
    parser.add_argument("domainName", type=str)
    parser.add_argument("sleepTime", type=float)
    parser.add_argument("cookieRotationProbability", type=float)

    return parser.parse_args()


def main():
    args = initArgs()
    idCount = args.cookiesNumber
    kafka_bootstrap_servers = [f"{args.kafka}:{args.kafkaPort}"]
    domain = args.domainName
    sleepTime = args.sleepTime
    cookieRotationProbability = args.cookieRotationProbability * sleepTime

    urlParamsOptions = OrderedDict([("", 0.8), ("?testVersion=a", 0.10), ("?testVersion=b", 0.10), ])
    refOptions = OrderedDict([("", 0.3), ("facebook.com", 0.10), ("google.com", 0.10), (domain, 0.50)])

    #define new provider to assure that cookies have the same userAgent all the time
    cookie_ua_provider = CookieUaProvider(
        provider_name="cookie_ua",
        initElemCount=idCount
    )
    fake = Faker()
    fake.add_provider(cookie_ua_provider)

    producer = KafkaProducer(bootstrap_servers=kafka_bootstrap_servers,
                            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                            api_version=(2, 6, 0))

    print("Producer started")

    try:
        while True:
            cookieID, ua, activityLevel = fake.cookie_ua()
            if activityLevel > random.random():
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
            if cookieRotationProbability > random.random():
                cookie_ua_provider.replace_random_elements()
            sleep(sleepTime)

    except KeyboardInterrupt:
        pass
        producer.close()


if __name__ == '__main__':
    main()
