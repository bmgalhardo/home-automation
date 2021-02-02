import os

UPDATE_PERIOD = int(os.getenv('UPDATE_PERIOD', 5))
DISCOVERY_PERIOD = int(os.getenv('DISCOVERY_PERIOD', 10))
SERVER_PORT = int(os.getenv('SERVER_PORT', 9999))
BULB_CONTROLLER = os.getenv('BULB_CONTROLLER', "http://localhost:5000")
EDP_CONTROLLER = os.getenv('EDP_CONTROLLER', "http://localhost:5000")
PLUG_CONTROLLER = os.getenv('PLUG_CONTROLLER', "http://localhost:5000")