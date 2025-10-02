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

c = Consumer({
        'bootstrap.servers': '13.49.128.80:19093,13.49.128.80:29093,13.49.128.80:39093',
        'group.id': 'group5_123456',
        'auto.offset.reset': 'latest',
        'security.protocol': 'SSL',
        'ssl.ca.location': '/app/auth/ca.crt',
        'ssl.keystore.location': '/app/auth/kafka.keystore.pkcs12',
        'ssl.keystore.password': 'cc2023',
        'enable.auto.commit': 'true',
        'ssl.endpoint.identification.algorithm': 'none',
})

conn = pymongo.MongoClient('mongodb://mongodb-0.mongodb:27017/test?gssapiServiceName=mongodb') 
print("ESTABLISHED CONNECTION TO DATABASE")

db = conn["test"]
experiments = db["experiments"]
experiments_records = db["records"]

experiment_data = {}
notications_headers = {
    "accept": "*/*",
    "Content-Type": "application/json; charset=utf-8"
}
notifications_url = "https://notifications-service.cc2023.4400app.me/api/notify?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3MDQxMjk4MTgsInN1YiI6Imdyb3VwNSJ9.DrVy8OQ0PogfqPm8RxTIxPhOIhDgXA7fZPezrGQY0ZcxDBOxsu99whwG6akmGcUz-Wl7mo6-U8qeU8XPeU9bHGoSxKb9Ng2k3KIHfks5jkqduwwIibTR1vGxKZXyT5NcBKFFT62H_OCmKv41YIOdtHNh165ixlS0KJQjGrOQQMi63zBREb26yFcfbDoLSlEffjRcl3r4jBj1YE61tSufTpCbGp4H2LxIT0tKUGzXvF2fu1y993j3er7vNiEZiPh_XrdlGEhPHMFLDig662R_CNV_-rfEQvI_FkpsH6ZJ-tageYUTWhVfuBXy-0dA3LdC_pC_Ir2XprmEy1qOXuofYg"

def decode(msg_value, header):
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
        #if you add experiment terminated you can empty the experiment_data[exp_id] for that ID IMPOTANT TO FIX SINCE EXPERIMENTS_DATA CAN GET HUGE
        elif header == "experiment_started":
            experiment_data[exp_id]["stabilized"] = True
        elif header == "sensor_temperature_measured":
            #Add weighted temperature to AverageTemp and add one to sensors so far           
            experiment_data[exp_id]["average_temp"] = experiment_data[exp_id]["average_temp"] + msg["temperature"] / experiment_data[exp_id]["nr_sensors"]
            experiment_data[exp_id]["sensors_counted"] = experiment_data[exp_id]["sensors_counted"] + 1

            #if all sensors have been measured, we can reset the counter and aggregate
            if experiment_data[exp_id]["sensors_counted"] == experiment_data[exp_id]["nr_sensors"]:
                print("---ALL SENSORS MEASURED---")              
                #if we are stabilizing, have not previously stabilized and are above the MinTemp (assume we approach from below)
                if experiment_data[exp_id]["stabilized"] == False and (experiment_data[exp_id]["average_temp"] > experiment_data[exp_id]["temp_min_threshold"] and  experiment_data[exp_id]["average_temp"] < experiment_data[exp_id]["temp_max_threshold"]):
    #               Notification on Stab
                    notifications_data = {
                        "notification_type": "Stabilized",
                        "researcher": experiment_data[exp_id]["researcher"],
                        "measurement_id": msg["measurement_id"],
                        "experiment_id" : exp_id,
                        "cipher_data" : msg["measurement_hash"]
                    }
                    response = requests.post(notifications_url, headers=notications_headers, json = notifications_data)
                    print(response.status_code)
                    print(response.text)
                    print("---STABILIZED---")
                    #State that we have now sent the message so no need to send it again
                    experiment_data[exp_id]["stabilized"] = True
                #if we are experimenting
                elif experiment_data[exp_id]["stabilized"] == True:
                    print("---EXPERIMENT STARTED---")
                    #if we are OOR
                    if (experiment_data[exp_id]["average_temp"] > experiment_data[exp_id]["temp_max_threshold"]) or (experiment_data[exp_id]["average_temp"] < experiment_data[exp_id]["temp_min_threshold"]):
                        #note that we are currently OOR, for DB purposes
                        experiment_data[exp_id]["currently_oor"] = True
                        #if we were previously in range:
                        if experiment_data[exp_id]["previously_oor"] == False:

                            notifications_data = {
                                "experiment_id" : exp_id,
                                "notification_type": "OutOfRange",
                                "researcher": experiment_data[exp_id]["researcher"],
                                "measurement_id": msg["measurement_id"],
                                "cipher_data" : msg["measurement_hash"]
                            }
                            response = requests.post(notifications_url, headers=notications_headers, json = notifications_data)
                            print(response.status_code)
                            print(response.text)
                            print(experiment_data)
                            print("---OUT OF RANGE ---")

                        experiment_data[exp_id]["previously_oor"] = True    
                    else:
                        experiment_data[exp_id]["previously_oor"] = False

                    experiments_records.insert_one({"exp_id" : exp_id, "timestamp" : msg["timestamp"],  "avg_temperature" : experiment_data[exp_id]["average_temp"]})
                #After checking all cases, reset AverageTemp and SensorSoFar  
                experiment_data[exp_id]["average_temp"] = 0
                experiment_data[exp_id]["sensors_counted"] = 0
        elif header == "experiment_terminated":
            experiments.insert_one(experiment_data[exp_id])

c.subscribe(
        ["experiment"], 
        on_assign=lambda _, p_list: print(p_list)
    )
while True:
    try:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue
        header = (msg.headers()[0][1].decode("utf-8"))
        print(header)
        decode(msg.value(), header)
    except:
        continue

