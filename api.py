from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import json

app = Flask(__name__)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client["test"]
experiments_records = db["records"]

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)

app.json_encoder = JSONEncoder

@app.route('/temperature')
def get_temperature():
    try:
        experiment_id = request.args.get('experiment-id')
        start_time = float(request.args.get('start-time'))
        end_time = float(request.args.get('end-time'))
        
        # Query for temperature measurements within time range
        records = experiments_records.find({
            "exp_id": experiment_id,
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }).sort("timestamp", 1)
        
        result = [
            {"timestamp": record["timestamp"], "temperature": record["avg_temperature"]}
            for record in records
        ]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/temperature/out-of-range')
def get_out_of_range():
    try:
        experiment_id = request.args.get('experiment-id')
        
        # This would need your business logic to determine out-of-range measurements
        # For now, returning empty array - you'll need to implement this
        records = experiments_records.find({
            "exp_id": experiment_id
        }).sort("timestamp", 1)
        
        # You need to store threshold info to determine out-of-range
        result = [
            {"timestamp": record["timestamp"], "temperature": record["avg_temperature"]}
            for record in records
            # Add your out-of-range logic here
        ]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3003, debug=True)