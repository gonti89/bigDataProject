#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import json
from collections import Counter
import matplotlib.pyplot as plt

figsize=(8,3)
counters = dict()
for k in ["time", "cookieID", "userAgent", "url", "referer", "ip"]:
    counters[k] = Counter()

with open("testData.txt") as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        for k,v in data.items():
            counters[k].update([v])

(
    pd
    .DataFrame(counters["time"], 
               index=["count"])
    .T
    .reset_index()
    .rename(columns={"index": "ts"})
    .assign(datetime=lambda x:pd.to_datetime(x["ts"], unit='s'))
    .set_index("datetime")
    .drop(columns=["ts"])
    .plot(kind="line", figsize=figsize, grid=True)
)
plt.tight_layout()
plt.savefig("eventOverTime.png")
plt.close()


(
    pd
    .DataFrame(counters["cookieID"], index=["count"])
    .T
    .sort_values("count", ascending=False)
    .reset_index(drop=True)
    .plot(kind="line", grid=True, figsize=figsize)
)
plt.tight_layout()
plt.savefig("eventDistributionOnCookies.png")
plt.close()


(
    pd
    .DataFrame(counters["userAgent"], index=["count"])
    .T
    .sort_values("count", ascending=False)
    .reset_index(drop=True)
    .plot(kind="line", grid=True, figsize=figsize)
)
plt.tight_layout()
plt.savefig("userAgentDistribution.png")
plt.close()


(
    pd
    .DataFrame(counters["url"], index=["count"])
    .T
    .sort_values("count", ascending=False)
    .reset_index(drop=True)
    .plot(kind="line", grid=True, figsize=figsize)
)

plt.tight_layout()
plt.savefig("urlsDistribution.png")
plt.close()


(
    pd
    .DataFrame(counters["url"], index=["count"])
    .T
    .sort_values("count", ascending=False)
    .reset_index(drop=False)
    .assign(url=lambda x:x["index"].str.split("?").str[0])
    .groupby("url")
    .agg(count=("count", "sum"))
    .sort_values("count", ascending=False)
    .reset_index(drop=True)
    .plot(kind="line", grid=True, figsize=figsize)
)
plt.tight_layout()
plt.savefig("urlsDistributionNoParams.png")
plt.close()


(
    pd
    .DataFrame(counters["referer"], index=["count"])
    .T
    .sort_values("count", ascending=False)
    .plot(kind="bar", grid=True, figsize=figsize)
)

plt.tight_layout()
plt.savefig("refererDistribution.png")
plt.close()


ipCount = len(counters["ip"])
eventCount = sum(counters["cookieID"].values())

print(f'eventCount = {eventCount}, ipCount={ipCount}')



