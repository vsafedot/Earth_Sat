from sgp4.api import Satrec, jday
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


class SatelliteTracker:
    def __init__(self):
        self.earth_radius = 6378.137  # Earth's radius in km
        self.e2 = 0.08181919 ** 2  # Earth's eccentricity squared

    def eci_to_lla(self, r, gst):
        """Convert Earth-Centered Inertial (ECI) coordinates to Lat/Lon/Alt."""
        x, y, z = r

        # Longitude calculation
        lon = np.arctan2(y, x) - np.deg2rad(gst)

        # Latitude calculation (iterative solution)
        p = np.sqrt(x ** 2 + y ** 2)
        lat = np.arctan2(z, p * (1 - self.e2))
        for _ in range(5):
            sin_lat = np.sin(lat)
            lat = np.arctan2(z + self.e2 * self.earth_radius * sin_lat, p)

        # Altitude calculation
        sin_lat = np.sin(lat)
        N = self.earth_radius / np.sqrt(1 - self.e2 * sin_lat ** 2)
        alt = p / np.cos(lat) - N

        return np.degrees(lat), np.degrees(lon) % 360, alt

    def calculate_ground_track(self, satellite, start_time, duration_hours=24, step_minutes=10):
        """Calculate satellite ground track over time."""
        positions = []
        times = []

        for minutes in range(0, duration_hours * 60, step_minutes):
            current_time = start_time + timedelta(minutes=minutes)
            jd, fr = jday(current_time.year, current_time.month, current_time.day,
                          current_time.hour, current_time.minute, current_time.second)

            # Calculate GST
            gst = (jd + fr - 2451545.0) / 36525.0 * 360.0
            gst %= 360.0

            # Get satellite position
            e, r, v = satellite.sgp4(jd, fr)

            if e == 0:  # Successful computation
                lat, lon, alt = self.eci_to_lla(r, gst)
                positions.append((lat, lon, alt))
                times.append(current_time)

        return positions, times

    def is_visible(self, sat_lla, ground_station_lla, min_elevation=10):
        """Determine if satellite is visible from ground station."""
        sat_lat, sat_lon, sat_alt = sat_lla
        gs_lat, gs_lon, _ = ground_station_lla

        # Convert to radians
        sat_lat, sat_lon = np.radians(sat_lat), np.radians(sat_lon)
        gs_lat, gs_lon = np.radians(gs_lat), np.radians(gs_lon)

        # Calculate great circle distance
        dlat = sat_lat - gs_lat
        dlon = sat_lon - gs_lon
        a = np.sin(dlat / 2) ** 2 + np.cos(gs_lat) * np.cos(sat_lat) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distance = self.earth_radius * c

        # Calculate elevation angle
        elevation = np.degrees(np.arctan2(sat_alt, distance))

        return elevation >= min_elevation, elevation

    def create_visualization(self, tle_list, ground_stations=None):
        """Create an interactive visualization of satellites and their ground tracks."""
        if ground_stations is None:
            ground_stations = [
                ("Kennedy Space Center", 28.5729, -80.6490),
                ("Guiana Space Centre", 5.2322, -52.7693)
            ]

        now = datetime.utcnow()

        # Create figure with secondary y-axis
        fig = make_subplots(rows=2, cols=1,
                            specs=[[{"type": "scattergeo"}],
                                   [{"type": "scatter"}]],
                            row_heights=[0.7, 0.3],  # Fixed: Changed 'heights' to 'row_heights'
                            subplot_titles=("Satellite Positions and Ground Tracks",
                                            "Satellite Altitudes vs Time"))

        # Add map to first subplot
        fig.update_geos(
            projection_type="orthographic",
            showland=True,
            showcountries=True,
            showocean=True,
            showcoastlines=True,
            landcolor="rgb(243, 243, 243)",
            oceancolor="rgba(204, 229, 255, 0.5)",
            countrycolor="rgb(204, 204, 204)",
            coastlinecolor="rgb(51, 51, 51)",
            lataxis_showgrid=True,
            lonaxis_showgrid=True
        )

        # Process each satellite
        for i, tle in enumerate(tle_list):
            satellite = Satrec.twoline2rv(tle[0], tle[1])
            positions, times = self.calculate_ground_track(satellite, now)

            # Separate positions into components
            lats, lons, alts = zip(*positions)

            # Add current position
            fig.add_trace(
                go.Scattergeo(
                    lat=[lats[0]],
                    lon=[lons[0]],
                    mode='markers+text',
                    text=[f"Satellite {i + 1}"],
                    textposition="top center",
                    marker=dict(size=10, symbol='diamond'),
                    name=f"Satellite {i + 1} (Current)",
                    showlegend=True
                ),
                row=1, col=1
            )

            # Add ground track
            fig.add_trace(
                go.Scattergeo(
                    lat=lats,
                    lon=lons,
                    mode='lines',
                    line=dict(width=1, dash='dot'),
                    name=f"Satellite {i + 1} Ground Track",
                    showlegend=True
                ),
                row=1, col=1
            )

            # Add altitude plot
            time_differences = [(t - now).total_seconds() / 3600 for t in times]
            fig.add_trace(
                go.Scatter(
                    x=time_differences,
                    y=alts,
                    name=f"Satellite {i + 1} Altitude",
                    mode='lines'
                ),
                row=2, col=1
            )

        # Add ground stations
        for name, lat, lon in ground_stations:
            fig.add_trace(
                go.Scattergeo(
                    lat=[lat],
                    lon=[lon],
                    mode='markers+text',
                    text=[name],
                    textposition="bottom center",
                    marker=dict(size=8, symbol='star'),
                    name=f"Ground Station: {name}",
                    showlegend=True
                ),
                row=1, col=1
            )

        # Update layout
        fig.update_layout(
            title="Advanced Satellite Tracking Visualization",
            height=900,
            xaxis2_title="Time from Now (hours)",
            yaxis2_title="Altitude (km)",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.01
            )
        )

        return fig


# Example usage
if __name__ == "__main__":
    # Example TLEs (add more as needed)
    tle_list = [
        ("1 25544U 98067A   20357.73333202  .00001264  00000-0  29611-4 0  9993",
         "2 25544  51.6450  61.5860 0002686  73.8743  54.5272 15.48947260260233"),  # ISS
        ("1 43017U 17073A   20357.73427318  .00000042  00000-0  00000-0 0  9991",
         "2 43017  53.0537 241.3127 0002602  55.2717 304.8218 15.06330636235390"),  # STARLINK
    ]

    # Create tracker and visualization
    tracker = SatelliteTracker()
    fig = tracker.create_visualization(tle_list)
    fig.show()