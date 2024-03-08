#!/usr/bin/env python3
from flask import Flask, request
import requests
import xmltodict
from datetime import datetime, timedelta
import math
import logging
import json
from geopy.geocoders import Nominatim
from astropy import coordinates as coord
from astropy import units as u
from astropy.time import Time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

def download_iss_data(url: str) -> bytes:
    """Download ISS data from the provided URL.

    Args:
        url (str): The URL from which to download the data.

    Returns:
        bytes: The downloaded data.

    """
    logging.info("Downloading ISS data...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logging.error(f"Failed to download ISS data: {e}")
        return None
    
def parse_xml_data(xml_data: bytes) -> list:
    """Parse the XML data and store it in list-of-dictionaries format.

    Args:
        xml_data (bytes): The XML data to parse.

    Returns:
        list: List of dictionaries containing parsed data.

    """
    logging.info("Parsing XML data...")
    data = []
    xml_dict = xmltodict.parse(xml_data)
    epochs = xml_dict["ndm"]["oem"]["body"]["segment"]["data"]["stateVector"]
    for t in epochs:
        # Extract data from each entry and store in dictionary
        t_data = {
            "EPOCH": t["EPOCH"],
            "X": float(t["X"]["#text"]),
            "Y": float(t["Y"]["#text"]),
            "Z": float(t["Z"]["#text"]),
            "X_DOT": float(t["X_DOT"]["#text"]),
            "Y_DOT": float(t["Y_DOT"]["#text"]),
            "Z_DOT": float(t["Z_DOT"]["#text"])
        }
        data.append(t_data)
    return data

def calculate_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    """Calculate speed from Cartesian velocity vectors.

    Args:
        x_dot (float): Velocity along the X-axis.
        y_dot (float): Velocity along the Y-axis.
        z_dot (float): Velocity along the Z-axis.

    Returns:
        float: The calculated speed.

    """
    return math.sqrt(x_dot**2 + y_dot**2 + z_dot**2)

def calculate_location(data) -> tuple:
    """
    Convert Cartesian coordinates to geodetic coordinates (latitude, longitude, altitude)
    and determine the geoposition (address) given the latitude and longitude.

    Args:
    - data (dict): The dictionary containing the Cartesian coordinates (X, Y, Z) and EPOCH.

    Returns:
    - tuple: A tuple containing the latitude (float), longitude (float), altitude (float), 
             and geoposition (str).
    """
    epoch = Time(datetime.strptime(data['EPOCH'], "%Y-%jT%H:%M:%S.%fZ"))
    xyz = [data['X'], data['Y'], data['Z']]
    
    cartrep = coord.CartesianRepresentation(*xyz, unit=u.km)
    gcrs = coord.GCRS(cartrep, obstime = epoch)
    itrs = gcrs.transform_to(coord.ITRS(obstime = epoch))
    loc = coord.EarthLocation(*itrs.cartesian.xyz)
    lat, lon, alt = loc.lat.value, loc.lon.value, loc.height.value

    # Reverse geocoding using Nominatim
    geolocator = Nominatim(user_agent="geo_reverse")
    location = geolocator.reverse((lat, lon),language='en')

    # Return as a tuple with the geoposition string formatted without changing the signs
    return lat, lon, alt, location.address if location else "Address not found"

def get_current_info(data: list) -> tuple:
    """Get information about the closest epoch to the current time.

    Args:
        data (list): List of dictionaries containing parsed data.

    Returns:
        tuple: A tuple containing the closest epoch dictionary and the instantaneous speed.

    """
    logging.info("Getting closest epoch info...")
    current_time = datetime.utcnow()
    closest = None
    min_diff = timedelta.max

    for t in data:
        epoch_t = datetime.strptime(t['EPOCH'], "%Y-%jT%H:%M:%S.%fZ")
        diff = current_time - epoch_t
        if diff < -timedelta(minutes=4, milliseconds=1):
            break
        if abs(diff) < min_diff:
            min_diff = diff
            closest = t
    
    # Calculate the instantaneous speed closest to the current time
    speed = calculate_speed(closest["X_DOT"], closest["Y_DOT"], closest["Z_DOT"])

    return closest, speed

@app.route('/comment',methods=['GET'])
def get_comments():
    """Return all the comments in the ISS Trajectory Data file."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        xml_dict = xmltodict.parse(iss_data)
        comments = []
        data = xml_dict["ndm"]["oem"]["body"]["segment"]["data"]["COMMENT"]
        if isinstance(data, list):  # Check if there are multiple comments
            for comment in data:
                if comment:  # Exclude null comments
                    comments.append(comment)  # Remove leading/trailing whitespace
        else:  # Single comment
            comments.append(data)
        return comments
    else:
        return "Failed to download ISS data.", 500
    
@app.route('/header',methods=['GET'])
def get_header():
    """Return the header of the ISS Trajectory Data file."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        xml_dict = xmltodict.parse(iss_data)
        header = xml_dict["ndm"]["oem"]["header"]
        return header
    else:
        return "Failed to download ISS data.", 500

@app.route('/metadata',methods=['GET'])
def get_metadata():
    """Return all the metadata in the ISS Trajectory Data file."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        xml_dict = xmltodict.parse(iss_data)
        metadata = xml_dict["ndm"]["oem"]["body"]["segment"]["metadata"]
        return metadata
    else:
        return "Failed to download ISS data.", 500

@app.route('/epochs', methods=['GET'])
def get_epochs():
    """Return entire data set or modified list of Epochs given query parameters."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        parsed_data = parse_xml_data(iss_data)
        try:
            limit = int(request.args.get('limit', len(parsed_data)))
            offset = int(request.args.get('offset', 0))
        except:
            return "Invalid paramters; limit and offset must be integers.", 500 
        
        if limit == len(parsed_data) and offset == 0:
            # Return entire data set
            return json.dumps(parsed_data), 200
        else:
            # Return modified list of Epochs
            modified_data = parsed_data[offset:offset+limit]
            return json.dumps(modified_data)+"\n", 200
    else:
        return "Failed to download ISS data.", 500

@app.route('/epochs/<epoch>', methods=['GET'])
def get_epoch(epoch):
    """Return state vectors for a specific Epoch from the data set."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        parsed_data = parse_xml_data(iss_data)
        for data in parsed_data:
            if data["EPOCH"] == epoch:
                return json.dumps(data), 200
        return "Epoch not found.", 404
    else:
        return "Failed to download ISS data.", 500

@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_epoch_speed(epoch):
    """Return instantaneous speed for a specific Epoch in the data set."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        parsed_data = parse_xml_data(iss_data)
        for data in parsed_data:
            if data["EPOCH"] == epoch:
                speed = math.sqrt(data["X_DOT"]**2 + data["Y_DOT"]**2 + data["Z_DOT"]**2)
                return json.dumps({"speed": speed}), 200
        return "Epoch not found.", 404
    else:
        return "Failed to download ISS data.", 500

@app.route('/epochs/<epoch>/location', methods=['GET'])
def get_epoch_location(epoch):
    """Return latitude, longitude, altitude, and geoposition for a specific Epoch in the data set"""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        parsed_data = parse_xml_data(iss_data)
        for data in parsed_data:
            if data["EPOCH"] == epoch:   
                lat, long, alt, geo = calculate_location(data)

                # Construct the response
                response = {
                    "latitude": lat,
                    "longitude": long,
                    "altitude": alt,
                    "geoposition": geo
                }
                
                return json.dumps(response), 200
        return "Epoch not found.", 404
    else:
        return "Failed to download ISS data.", 500

@app.route('/now', methods=['GET'])
def get_nearest_epoch():
    """Return state vectors and instantaneous speed for the Epoch that is nearest in time."""
    iss_data = download_iss_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    if iss_data:
        parsed_data = parse_xml_data(iss_data)
        closest, speed = get_current_info(parsed_data)

        # Get epoch location information
        lat, long, alt, geo = calculate_location(closest)

        # Construct the response
        response = {
            "closest_epoch": closest["EPOCH"],
            "latitude": lat,
            "longitude": long,
            "altitude": alt,
            "geoposition": geo,
            "speed": speed
        }

        return json.dumps(response), 200
    else:
        return "Failed to download ISS data.", 500
        
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')