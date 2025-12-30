# Create a obs.conf file
- need this:
{
  "host": "192.168.1.x",
  "port": 4455,
  "password": "xxxxxxxx"
}
You find them inside your OBS websocket

# Use venv
python -m venv venv

# Activate venv
source venv/Scripts/activate 

# Install the plugins from Requirements.txt
pip install -r requirements.txt

# Activate the program
py __main__.py (if your on Windows) otherwise use __elgato_version__.py (Linux version)
