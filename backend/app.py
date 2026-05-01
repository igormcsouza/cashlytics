import os
from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["cashlytics"]
expenses_col = db["expenses"]


REQUIRED_FIELDS = ("description", "deadline", "value", "recurrent")


def validate_expense(data):
    if data is None:
        return "Request body is required"
    for field in REQUIRED_FIELDS:
        if field not in data:
            return f"Missing required field: {field}"
    try:
        float(data["value"])
    except (TypeError, ValueError):
        return "Field 'value' must be a number"
    return None


def serialize(expense):
    expense["_id"] = str(expense["_id"])
    return expense


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/expenses", methods=["GET"])
def get_expenses():
    expenses = [serialize(e) for e in expenses_col.find()]
    return jsonify(expenses)


@app.route("/expenses", methods=["POST"])
def create_expense():
    data = request.get_json()
    error = validate_expense(data)
    if error:
        return jsonify({"error": error}), 400
    result = expenses_col.insert_one(
        {
            "description": data["description"],
            "deadline": data["deadline"],
            "value": float(data["value"]),
            "recurrent": bool(data["recurrent"]),
        }
    )
    expense = expenses_col.find_one({"_id": result.inserted_id})
    return jsonify(serialize(expense)), 201


@app.route("/expenses/<expense_id>", methods=["PUT"])
def update_expense(expense_id):
    try:
        oid = ObjectId(expense_id)
    except InvalidId:
        return jsonify({"error": "Invalid expense ID"}), 400
    data = request.get_json()
    error = validate_expense(data)
    if error:
        return jsonify({"error": error}), 400
    result = expenses_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "description": data["description"],
                "deadline": data["deadline"],
                "value": float(data["value"]),
                "recurrent": bool(data["recurrent"]),
            }
        },
    )
    if result.matched_count == 0:
        return jsonify({"error": "Not found"}), 404
    expense = expenses_col.find_one({"_id": oid})
    return jsonify(serialize(expense))


@app.route("/expenses/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    try:
        oid = ObjectId(expense_id)
    except InvalidId:
        return jsonify({"error": "Invalid expense ID"}), 400
    result = expenses_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"error": "Not found"}), 404
    return "", 204


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
