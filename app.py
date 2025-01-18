# from flask import Flask, jsonify, render_template_string, request
# from skyfield.api import load, wgs84, EarthSatellite
# import requests
#
# app = Flask(__name__)
#
# # URL to fetch TLE data
# TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle"
#
# # Satellite data and timescale
# satellites = {}
# ts = load.timescale()
#
#
# def load_tle_data():
#     """Load TLE data from the internet and store satellite objects."""
#     global satellites
#     try:
#         response = requests.get(TLE_URL)
#         response.raise_for_status()
#         tle_lines = response.text.splitlines()
#
#         satellites.clear()
#         for i in range(0, len(tle_lines), 3):
#             if i + 2 >= len(tle_lines):
#                 break
#             name = tle_lines[i].strip()
#             line1 = tle_lines[i + 1].strip()
#             line2 = tle_lines[i + 2].strip()
#             satellites[name] = EarthSatellite(line1, line2, name, ts)
#
#         print(f"Loaded {len(satellites)} satellites.")
#     except Exception as e:
#         print(f"Error loading TLE data: {e}")
#
#
# @app.route("/")
# def index():
#     """Render the main web page."""
#     satellite_names = list(satellites.keys())
#     return render_template_string("""
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#         <meta charset="UTF-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <title>Satellite Tracker</title>
#         <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
#         <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
#         <style>
#             body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
#             #map { height: 90vh; width: 100%; }
#             .controls { margin: 10px; }
#         </style>
#     </head>
#     <body>
#         <div class="controls">
#             <label for="satellite">Select Satellite:</label>
#             <select id="satellite">
#                 {% for sat in satellites %}
#                     <option value="{{ sat }}">{{ sat }}</option>
#                 {% endfor %}
#             </select>
#             <button onclick="startTracking()">Start Tracking</button>
#         </div>
#         <div id="map"></div>
#
#         <script>
#             let map = L.map('map').setView([0, 0], 2);
#             L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
#                 maxZoom: 19,
#             }).addTo(map);
#
#             let marker = null;
#             let trackLine = L.polyline([], { color: 'blue' }).addTo(map);
#
#             async function startTracking() {
#                 const satellite = document.getElementById("satellite").value;
#                 if (!satellite) {
#                     alert("Please select a satellite first.");
#                     return;
#                 }
#
#                 const track = async () => {
#                     const response = await fetch('/get_position', {
#                         method: 'POST',
#                         headers: { 'Content-Type': 'application/json' },
#                         body: JSON.stringify({ satellite }),
#                     });
#                     const data = await response.json();
#
#                     if (data.error) {
#                         console.error(data.error);
#                         return;
#                     }
#
#                     const { latitude, longitude } = data;
#
#                     if (marker) {
#                         marker.setLatLng([latitude, longitude]);
#                     } else {
#                         marker = L.marker([latitude, longitude]).addTo(map);
#                     }
#
#                     trackLine.addLatLng([latitude, longitude]);
#                     map.setView([latitude, longitude], map.getZoom());
#
#                     setTimeout(track, 1000);
#                 };
#
#                 track();
#             }
#         </script>
#     </body>
#     </html>
#     """, satellites=satellite_names)
#
#
# @app.route("/get_position", methods=["POST"])
# def get_position():
#     """API endpoint to fetch the current position of a satellite."""
#     try:
#         data = request.get_json()
#         satellite_name = data.get("satellite")
#         if not satellite_name or satellite_name not in satellites:
#             return jsonify({"error": "Invalid satellite name"}), 400
#
#         satellite = satellites[satellite_name]
#         t = ts.now()
#         geocentric = satellite.at(t)
#         subpoint = wgs84.subpoint_of(geocentric)
#
#         return jsonify({
#             "latitude": subpoint.latitude.degrees,
#             "longitude": subpoint.longitude.degrees,
#             "altitude": subpoint.elevation.km
#         })
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#
#
# if __name__ == "__main__":
#     load_tle_data()
#     app.run(debug=True)


from flask import Flask, jsonify, render_template_string, request
import requests
from datetime import datetime
from skyfield.api import load, EarthSatellite

app = Flask(__name__)

# URL to fetch TLE data
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle"

# Satellite data and timescale
satellites = {}
ts = load.timescale()


def load_tle_data():
    """Load TLE data from the internet and store satellite objects."""
    global satellites
    try:
        response = requests.get(TLE_URL)
        response.raise_for_status()
        tle_lines = response.text.splitlines()

        satellites.clear()
        for i in range(0, len(tle_lines), 3):
            if i + 2 >= len(tle_lines):
                break
            name = tle_lines[i].strip()
            line1 = tle_lines[i + 1].strip()
            line2 = tle_lines[i + 2].strip()
            satellites[name] = EarthSatellite(line1, line2, name, ts)

        print(f"Loaded {len(satellites)} satellites.")
    except Exception as e:
        print(f"Error loading TLE data: {e}")


@app.route("/")
def index():
    """Render the main web page."""
    satellite_names = list(satellites.keys())
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Satellite Tracker</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
            #map { height: 90vh; width: 100%; }
            .controls { margin: 10px; }
        </style>
    </head>
    <body>
        <div class="controls">
            <label for="satellite">Select Satellite:</label>
            <select id="satellite">
                {% for sat in satellites %}
                    <option value="{{ sat }}">{{ sat }}</option>
                {% endfor %}
            </select>
            <button onclick="startTracking()">Start Tracking</button>
        </div>
        <div id="map"></div>

        <script>
            let map = L.map('map').setView([0, 0], 2);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
            }).addTo(map);

            let marker = null;
            let trackLine = L.polyline([], { color: 'blue' }).addTo(map);

            async function startTracking() {
                const satellite = document.getElementById("satellite").value;
                if (!satellite) {
                    alert("Please select a satellite first.");
                    return;
                }

                const track = async () => {
                    const response = await fetch('/get_position', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ satellite }),
                    });
                    const data = await response.json();

                    if (data.error) {
                        console.error(data.error);
                        return;
                    }

                    const { latitude, longitude } = data;

                    if (marker) {
                        marker.setLatLng([latitude, longitude]);
                    } else {
                        marker = L.marker([latitude, longitude]).addTo(map);
                    }

                    trackLine.addLatLng([latitude, longitude]);
                    map.setView([latitude, longitude], map.getZoom());

                    setTimeout(track, 1000);
                };

                track();
            }
        </script>
    </body>
    </html>
    """, satellites=satellite_names)


@app.route("/get_position", methods=["POST"])
def get_position():
    """API endpoint to fetch the current position of a satellite."""
    try:
        data = request.get_json()
        satellite_name = data.get("satellite")
        if not satellite_name or satellite_name not in satellites:
            return jsonify({"error": "Invalid satellite name"}), 400

        satellite = satellites[satellite_name]
        tle_line1 = satellite.model.line1
        tle_line2 = satellite.model.line2

        # Use the SGP4 model to get the satellite position
        from segment1 import get_satellite_position  # Import the function from Segment 1

        lat, lon, alt = get_satellite_position(tle_line1, tle_line2)

        return jsonify({
            "latitude": lat,
            "longitude": lon,
            "altitude": alt
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    load_tle_data()
    app.run(debug=True)
