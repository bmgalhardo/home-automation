from fastapi import FastAPI
import uvicorn
from edp import EDPConnect

app = FastAPI()

EDP = EDPConnect.authenticate()


@app.get("/active_power")
def get_monthly_active_power():
    # TODO should be a post with contract and date period
    contract = "PT0002000013237426ED"
    total = EDP.get_monthly_active_power(contract)
    return {"total": total}


@app.get("/contracts")
def get_contracts():
    contracts = EDP.get_contracts()
    return contracts


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
