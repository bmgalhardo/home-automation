from flask import Flask, jsonify

from edp import EDPConnect

app = Flask(__name__)

EDP = EDPConnect.authenticate()


@app.route("/active_power", methods=['GET'])
def get_monthly_active_power():
    # TODO should be a post with contract and date period
    contract = "PT0002000013237426ED"
    total = EDP.get_monthly_active_power(contract)
    return {"total": total}, 200


@app.route("/contracts", methods=['GET'])
def get_contracts():
    formatted_data = jsonify(EDP.get_contracts())
    return formatted_data, 200
