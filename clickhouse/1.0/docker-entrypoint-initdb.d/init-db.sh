#!/bin/bash
set -e

clickhouse client -n <<-EOSQL
	CREATE DATABASE IF NOT EXISTS portal;
	CREATE TABLE portal.events_stream (
		time DateTime('UTC'), 
		cookieID UInt64, 
		userAgent String, 	
		url String, 
		referer String, 
		ip String) 
	ENGINE = Kafka 
	SETTINGS kafka_broker_list = 'kafka:29092', 
		kafka_topic_list = 'base_data', 
		kafka_format = 'JSONEachRow', 
		kafka_skip_broken_messages = 1, 
		kafka_num_consumers = 1, 
		kafka_group_name = 'kafka_group';
	CREATE TABLE portal.events AS portal.events_stream ENGINE = MergeTree()  ORDER BY time;
	CREATE MATERIALIZED VIEW portal.events_consumer 
		TO portal.events 
		AS SELECT *
		FROM portal.events_stream;
EOSQL
