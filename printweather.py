#!/usr/bin/env python3

import os
import sys
import struct
import subprocess
import tempfile
from datetime import datetime
import json
import urllib.request, urllib.parse, urllib.error

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.stderr.write("Error: The 'Pillow' library is not installed.\n")
    sys.stderr.write("Please install it, for example: 'pip install Pillow'\n")
    sys.exit(1)

# Constants
API_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_VARS = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_hours"
FORECAST_DAYS = "1"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ICON_BASE_URL = "https://github.com/erikflowers/weather-icons/raw/refs/heads/master/svg/"
ICON_NAMES = [
    "wi-cloudy.svg", "wi-day-cloudy.svg", "wi-day-rain.svg",
    "wi-day-showers.svg", "wi-day-snow.svg", "wi-day-sunny.svg", "wi-fog.svg",
    "wi-na.svg", "wi-rain.svg", "wi-showers.svg", "wi-sleet.svg",
    "wi-snow.svg", "wi-sprinkle.svg", "wi-storm-showers.svg",
    "wi-thunderstorm.svg",
]

def download_icons():
    """Downloads the necessary weather icons."""
    icons_dir = os.path.join(SCRIPT_DIR, "weather-icons", "svg")
    os.makedirs(icons_dir, exist_ok=True)
    print(f"Downloading icons to {icons_dir}...")
    for icon_name in ICON_NAMES:
        url = f"{ICON_BASE_URL}{icon_name}"
        dest_path = os.path.join(icons_dir, icon_name)
        try:
            sys.stdout.write(f"  Downloading {icon_name}...")
            sys.stdout.flush()
            with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            sys.stdout.write("done.\n")
        except urllib.error.URLError as e:
            sys.stderr.write(f"\nError downloading {icon_name}: {e}\n")
    print("Icon download complete.")
    sys.exit(0)

def check_dependencies():
    """Checks for external dependencies."""
    if not os.path.isdir(os.path.join(SCRIPT_DIR, "weather-icons", "svg")):
        sys.stderr.write("Error: weather-icons/svg directory not found.\n")
        sys.stderr.write(f"Please run 'printweather.py --download-icons' to download them.\n")
        sys.stderr.write("Or 'git clone https://github.com/erikflowers/weather-icons'.\n")
        sys.stderr.write("Or download the zip: https://github.com/erikflowers/weather-icons/archive/refs/heads/master.zip\n")
        sys.exit(1)

def get_config():
    """Gets config from command line args, environment variables, or defaults."""
    lat = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('LATITUDE', "51.5072")
    lon = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('LONGITUDE', "-0.1276")
    timezone = sys.argv[3] if len(sys.argv) > 3 else os.environ.get('TIMEZONE', "Europe/London")
    return lat, lon, timezone

def get_weather_icon_path(code):
    """Maps weather code to icon file path."""
    icon_map = {
        0: "wi-day-sunny.svg", 1: "wi-day-cloudy.svg", 2: "wi-cloudy.svg",
        3: "wi-cloudy.svg", 45: "wi-fog.svg", 48: "wi-fog.svg",
        51: "wi-sprinkle.svg", 53: "wi-sprinkle.svg", 55: "wi-sprinkle.svg",
        56: "wi-sleet.svg", 57: "wi-sleet.svg", 61: "wi-day-rain.svg",
        63: "wi-rain.svg", 65: "wi-rain.svg", 66: "wi-sleet.svg",
        67: "wi-sleet.svg", 71: "wi-snow.svg", 73: "wi-snow.svg",
        75: "wi-snow.svg", 77: "wi-snow.svg", 80: "wi-day-showers.svg",
        81: "wi-showers.svg", 82: "wi-showers.svg", 85: "wi-day-snow.svg",
        86: "wi-day-snow.svg", 95: "wi-thunderstorm.svg",
        96: "wi-storm-showers.svg", 99: "wi-storm-showers.svg",
    }
    icon_name = icon_map.get(code, "wi-na.svg")
    return os.path.join(SCRIPT_DIR, "weather-icons", "svg", icon_name)

def fetch_weather_data(latitude, longitude, timezone):
    """Fetches weather data from the Open-Meteo API."""
    params = {
        "latitude": latitude, "longitude": longitude, "daily": DAILY_VARS,
        "timezone": timezone, "forecast_days": FORECAST_DAYS,
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    response_text = ""
    try:
        with urllib.request.urlopen(url) as response:
            response_text = response.read().decode('utf-8')
        data = json.loads(response_text)
        if "error" in data:
            sys.stderr.write(f"Error from weather API: {data}\n")
            sys.exit(1)
        return data['daily']
    except urllib.error.URLError as e:
        sys.stderr.write(f"Error fetching weather data: {e}\n")
        sys.exit(1)
    except (KeyError, json.JSONDecodeError):
        sys.stderr.write(f"Unexpected API response format: {response_text}\n")
        sys.exit(1)

def convert_svg_to_png(svg_path):
    """Converts SVG to a temporary PNG file for printing."""
    fd, tmp_png_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)

    try:
        relative_svg_path = os.path.relpath(svg_path, SCRIPT_DIR)
        subprocess.run(
            [
                "convert", "-background", "white", "-density", "900",
                relative_svg_path, "-resize", "256x256", tmp_png_path,
            ],
            check=True, capture_output=True, text=True, cwd=SCRIPT_DIR
        )
        return tmp_png_path
    except FileNotFoundError:
        sys.stderr.write("Error: 'convert' command not found. ImageMagick is required.\n")
        sys.stderr.write("Please install ImageMagick.\n")
        os.remove(tmp_png_path)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error converting SVG to PNG: {e.stderr}\n")
        os.remove(tmp_png_path)
        sys.exit(1)

def print_image_and_cleanup(image_path):
    """Prints a raster image to an ESC-POS printer and cleans up the file."""
    try:
        im = Image.open(image_path)
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
        if im.mode != '1':
            im = im.convert('1')
        if im.size[0] % 8:
            im2 = Image.new('1', (im.size[0] + 8 - im.size[0] % 8, im.size[1]), 'white')
            im2.paste(im, (0, 0))
            im = im2
        im = ImageOps.invert(im.convert('L'))
        im = im.convert('1')

        header = b'\x1d\x76\x30\x00'
        width_bytes = struct.pack('2B', int(im.size[0] / 8) % 256, int(im.size[0] / (8 * 256)))
        height_bytes = struct.pack('2B', im.size[1] % 256, int(im.size[1] / 256))

        sys.stdout.buffer.write(header + width_bytes + height_bytes + im.tobytes())
    finally:
        os.remove(image_path)

def format_date_with_ordinal(d):
    """Formats date with ordinal suffix."""
    day = d.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    return d.strftime(f"%-d{suffix} %b %Y")

def main():
    """Main script execution."""
    if len(sys.argv) > 1 and sys.argv[1] == '--download-icons':
        download_icons()

    check_dependencies()

    lat, lon, timezone = get_config()
    daily_data = fetch_weather_data(lat, lon, timezone)

    weather_code = daily_data['weather_code'][0]
    temp_min = round(daily_data['temperature_2m_min'][0])
    temp_max = round(daily_data['temperature_2m_max'][0])
    precip_chance = daily_data['precipitation_probability_max'][0]
    precip_hours = daily_data['precipitation_hours'][0]

    weather_icon_svg_path = get_weather_icon_path(weather_code)
    weather_icon_png_path = convert_svg_to_png(weather_icon_svg_path)

    sys.stdout.buffer.write(b'\x1b\x7b\x01')
    sys.stdout.buffer.write(b'\x1d\x21\x11')
    sys.stdout.buffer.write(b'\n')
    sys.stdout.buffer.write(f"{precip_chance}% ({precip_hours}h)\n".encode("ascii"))
    sys.stdout.buffer.write(f"Min: {temp_min}\n".encode("ascii"))
    sys.stdout.buffer.write(f"Max: {temp_max}\n".encode("ascii"))

    print_image_and_cleanup(weather_icon_png_path)

    sys.stdout.buffer.write(b'\n')
    sys.stdout.buffer.write(f"{format_date_with_ordinal(datetime.now())}\n".encode("ascii"))
    sys.stdout.buffer.write(b'\x1d\x21\x00')
    sys.stdout.buffer.write(b'\x1b\x7b\x00')
    sys.stdout.buffer.write(b'\n\n\n')

if __name__ == "__main__":
    main()
