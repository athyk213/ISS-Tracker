import pytest
from iss_tracker import download_iss_data, parse_xml_data, calculate_speed, get_current_info, calculate_location
import requests

@pytest.fixture
def sample_xml_data():
    return b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ndm>
  <oem id="CCSDS_OEM_VERS" version="2.0">
    <body>
      <segment>
        <data>
          <stateVector>
            <EPOCH>2024-045T12:04:00.000Z</EPOCH>
            <X units="km">100.0</X>
            <Y units="km">200.0</Y>
            <Z units="km">300.0</Z>
            <X_DOT units="km/s">1.0</X_DOT>
            <Y_DOT units="km/s">2.0</Y_DOT>
            <Z_DOT units="km/s">3.0</Z_DOT>
          </stateVector>
          <stateVector>
            <EPOCH>2024-045T12:05:00.000Z</EPOCH>
            <X units="km">150.0</X>
            <Y units="km">250.0</Y>
            <Z units="km">350.0</Z>
            <X_DOT units="km/s">1.5</X_DOT>
            <Y_DOT units="km/s">2.5</Y_DOT>
            <Z_DOT units="km/s">3.5</Z_DOT>
          </stateVector>
        </data>
      </segment>
    </body>
  </oem>
</ndm>'''

BASE_URL = 'http://localhost:5000'

def test_download_iss_data():
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    assert download_iss_data(url) is not None

# Test function to parse XML data
def test_parse_xml_data(sample_xml_data):
    parsed_data = parse_xml_data(sample_xml_data)
    assert len(parsed_data) == 2
    assert isinstance(parsed_data[0], dict)
    assert parsed_data[0]["EPOCH"] == '2024-045T12:04:00.000Z'
    assert parsed_data[0]["X"] == 100.0
    assert parsed_data[0]["Y"] == 200.0
    assert parsed_data[0]["Z"] == 300.0
    assert parsed_data[0]["X_DOT"] == 1.0
    assert parsed_data[0]["Y_DOT"] == 2.0
    assert parsed_data[0]["Z_DOT"] == 3.0

# Test function for calculate_speed
def test_calculate_speed():
    assert calculate_speed(1.0, 2.0, 3.0) == pytest.approx(3.7416573867739413)

# Test function for calculate_location
def test_calculate_location(sample_xml_data):
    parsed_data = parse_xml_data(sample_xml_data)
    lat, lon, alt, geoposition = calculate_location(parsed_data[0])
    
    assert isinstance(lat, float)
    assert isinstance(lon, float)
    assert isinstance(alt, float)
    assert isinstance(geoposition, str)

    # Check if the calculated values are approximately equal to the expected values
    assert lat == pytest.approx(56.38422100482626)
    assert lon == pytest.approx(98.88694979985289)
    assert alt == pytest.approx(-5989.66879422592)
    assert geoposition == 'Каменское сельское поселение, Chunsky Rayon, Irkutsk Oblast, Siberian Federal District, Russia'


# Test function for get_current_info
def test_get_current_info(sample_xml_data):
    parsed_data = parse_xml_data(sample_xml_data)
    closest, instant_speed = get_current_info(parsed_data)
    assert closest is not None
    assert instant_speed is not None

### Routes Testing
    
import requests

# Test function for the /comment route
def test_comment_route():
    response = requests.get('http://localhost:5000/comment')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# Test function for the /header route
def test_header_route():
    response = requests.get('http://localhost:5000/header')
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

# Test function for the /metadata route
def test_metadata_route():
    response = requests.get('http://localhost:5000/metadata')
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

# Test function for the /epochs route
def test_epochs_route():
    response = requests.get('http://localhost:5000/epochs')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# Test function for the /epochs?limit=int&offset=int route
def test_epochs_limit_offset_route():
    response = requests.get('http://localhost:5000/epochs?limit=5&offset=0')
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 5

# Test function for the /epochs/<epoch> route
def test_epochs_epoch_route():
    response1 = requests.get('http://localhost:5000/epochs')
    if response1.status_code == 200:
        epoch = response1.json()[0]['EPOCH']
        response2 = requests.get('http://localhost:5000/epochs/' + epoch)
        assert response2.status_code == 200
        assert isinstance(response2.json(), dict)

# Test function for the /epochs/<epoch>/speed route
def test_epochs_epoch_speed_route():
    response1 = requests.get('http://localhost:5000/epochs')
    if response1.status_code == 200:
        epoch = response1.json()[0]['EPOCH']
        response2 = requests.get('http://localhost:5000/epochs/' + epoch + '/speed')
        assert response2.status_code == 200
        assert 'speed' in response2.json()

# Test function for the /epochs/<epoch>/location route
def test_epochs_epoch_location_route():
    response1 = requests.get('http://localhost:5000/epochs')
    if response1.status_code == 200:
        epoch = response1.json()[0]['EPOCH']
        response2 = requests.get('http://localhost:5000/epochs/' + epoch + '/location')
        assert response2.status_code == 200
        assert 'latitude' in response2.json()
        assert 'longitude' in response2.json()
        assert 'altitude' in response2.json()
        assert 'geoposition' in response2.json()

# Test function for the /now route
def test_now_route():
    response = requests.get('http://localhost:5000/now')
    assert response.status_code == 200
    assert 'latitude' in response.json()
    assert 'longitude' in response.json()
    assert 'altitude' in response.json()
    assert 'geoposition' in response.json()
