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
		ipHash Int64,
		shortIp String,
		deviceType String,
		os String,
		browser String) 
	ENGINE = Kafka 
	SETTINGS kafka_broker_list = 'kafka:29092', 
		kafka_topic_list = 'eventsDecorated', 
		kafka_format = 'JSONEachRow', 
		kafka_skip_broken_messages = 0, 
		kafka_num_consumers = 1, 
		kafka_group_name = 'kafka_group';

	CREATE TABLE portal.events AS portal.events_stream ENGINE = MergeTree()  ORDER BY time;

	CREATE MATERIALIZED VIEW portal.events_consumer 
		TO portal.events 
		AS SELECT *
		FROM portal.events_stream;

	CREATE TABLE portal.session_stream (
		cookieID UInt64, 
		deviceType String,
		os String,
		browser String,
		sessionStart DateTime('UTC'), 
		sessionEnd DateTime('UTC'), 
		sessionDuration UInt32,
		sessionUniqueUrlsCount UInt32 
		) 
	ENGINE = Kafka 
	SETTINGS kafka_broker_list = 'kafka:29092', 
		kafka_topic_list = 'sessionData', 
		kafka_format = 'JSONEachRow', 
		kafka_skip_broken_messages = 0,
		kafka_num_consumers = 1, 
		kafka_group_name = 'kafka_group';

	CREATE TABLE portal.session AS portal.session_stream ENGINE = MergeTree()  ORDER BY sessionStart;

	CREATE MATERIALIZED VIEW portal.session_consumer 
		TO portal.session 
		AS SELECT *
		FROM portal.session_stream;


EOSQL
