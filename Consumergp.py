import avro
import io
import json
from confluent_kafka import Consumer
import sys
import pymongo
import avro.schema
from avro.datafile import DataFileReader, DataFileWriter
from avro.io import DatumReader, DatumWriter, BinaryDecoder
import requests
import random
import time

# Updated Kafka configuration for demo
c = Consumer({
    "bootstrap.servers": "13.49.128.80:19093,13.49.128.80:29093,13.49.128.80:39093",
    "group.id": "group3",  # Use your actual group name
    "auto.offset.reset": "latest",
    "security.protocol": "SSL",
    "ssl.ca.location": "group3/ca.crt",  # or use the PKCS12 files
    "ssl.certificate.location": "group3/client.crt",
    "ssl.key.location": "group3/client.key", 
    "ssl.key.password": "cc2023",
    "ssl.endpoint.identification.algorithm": "none",
    "enable.auto.commit": True,
})


# MongoDB connection - check if this needs updating for demo
conn = pymongo.MongoClient('mongodb://localhost:27017/')  # Use local MongoDB for now
print("ESTABLISHED CONNECTION TO DATABASE")

db = conn["test"]
experiments = db["experiments"]
experiments_records = db["records"]

experiment_data = {}

# UPDATED: Demo notification URL - you need to get the token from group3/token file
# Check if you have a token file:
# cat group3/token
notifications_headers = {
    "accept": "*/*",
    "Content-Type": "application/json; charset=utf-8"
}

# UPDATED: Use the demo notification service URL
notifications_url = "https://notifications-service-cec.ad.dlandau.nl/api/notify?token=YOUR_ACTUAL_TOKEN"  # REPLACE WITH ACTUAL TOKEN

def decode(msg_value, header):
    # Your existing decode function remains the same
    events = DataFileReader(io.BytesIO(msg_value), DatumReader())
    print("---STARTING---")
    for msg in events:
        exp_id = msg["experiment"]
        if header == "experiment_configured":
            experiment_data[exp_id] = {
                "exp_id" : exp_id,
                "temp_min_threshold" : msg["temperature_range"]["lower_threshold"],
                "temp_max_threshold" : msg["temperature_range"]["upper_threshold"],
                "nr_sensors" : len(msg["sensors"]),
                "researcher" : msg["researcher"],
                "stabilized" : False,
                "currently_oor": False,
                "previously_oor": False,
                "average_temp" : 0,
                "sensors_counted" : 0,
            }
        elif header == "experiment_started":
            experiment_data[exp_id]["stabilized"] = True
        elif header == "sensor_temperature_measured":
            experiment_data[exp_id]["average_temp"] = experiment_data[exp_id]["average_temp"] + msg["temperature"] / experiment_data[exp_id]["nr_sensors"]
            experiment_data[exp_id]["sensors_counted"] = experiment_data[exp_id]["sensors_counted"] + 1

            if experiment_data[exp_id]["sensors_counted"] == experiment_data[exp_id]["nr_sensors"]:
                print("---ALL SENSORS MEASURED---")
                if experiment_data[exp_id]["stabilized"] == False and (experiment_data[exp_id]["average_temp"] > experiment_data[exp_id]["temp_min_threshold"] and  experiment_data[exp_id]["average_temp"] < experiment_data[exp_id]["temp_max_threshold"]):
                    notifications_data = {
                        "notification_type": "Stabilized",
                        "researcher": experiment_data[exp_id]["researcher"],
                        "measurement_id": msg["measurement_id"],
                        "experiment_id" : exp_id,
                        "cipher_data" : msg["measurement_hash"]
                    }
                    response = requests.post(notifications_url, headers=notifications_headers, json=notifications_data)
                    print(f"Stabilized notification: {response.status_code} - {response.text}")
                    experiment_data[exp_id]["stabilized"] = True
                elif experiment_data[exp_id]["stabilized"] == True:
                    print("---EXPERIMENT STARTED---")
                    if (experiment_data[exp_id]["average_temp"] > experiment_data[exp_id]["temp_max_threshold"]) or (experiment_data[exp_id]["average_temp"] < experiment_data[exp_id]["temp_min_threshold"]):
                        experiment_data[exp_id]["currently_oor"] = True
                        if experiment_data[exp_id]["previously_oor"] == False:
                            notifications_data = {
                                "experiment_id" : exp_id,
                                "notification_type": "OutOfRange",
                                "researcher": experiment_data[exp_id]["researcher"],
                                "measurement_id": msg["measurement_id"],
                                "cipher_data" : msg["measurement_hash"]
                            }
                            response = requests.post(notifications_url, headers=notifications_headers, json=notifications_data)
                            print(f"OutOfRange notification: {response.status_code} - {response.text}")
                            experiment_data[exp_id]["previously_oor"] = True
                    else:
                        experiment_data[exp_id]["previously_oor"] = False

                    experiments_records.insert_one({"exp_id" : exp_id, "timestamp" : msg["timestamp"],  "avg_temperature" : experiment_data[exp_id]["average_temp"]})
                
                experiment_data[exp_id]["average_temp"] = 0
                experiment_data[exp_id]["sensors_counted"] = 0
        elif header == "experiment_terminated":
            experiments.insert_one(experiment_data[exp_id])

# UPDATED: Subscribe to 'experiment' topic for demo
c.subscribe(["experiment"])

while True:
    try:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue
        header = (msg.headers()[0][1].decode("utf-8"))
        print(f"Received message: {header}")
        decode(msg.value(), header)
    except Exception as e:
        print(f"Error: {e}")
        continue