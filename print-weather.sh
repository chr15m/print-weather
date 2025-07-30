#!/bin/bash

set -euo pipefail

get_weather_icon_path() {
    local code=$1
    local icon_path="./weather-icons/svg/"
    local icon_name
    case $code in
        0) icon_name="wi-day-sunny.svg";;
        1) icon_name="wi-day-cloudy.svg";;
        2) icon_name="wi-cloudy.svg";;
        3) icon_name="wi-cloudy.svg";;
        45|48) icon_name="wi-fog.svg";;
        51|53|55) icon_name="wi-sprinkle.svg";;
        56|57) icon_name="wi-sleet.svg";;
        61) icon_name="wi-day-rain.svg";;
        63|65) icon_name="wi-rain.svg";;
        66|67) icon_name="wi-sleet.svg";;
        71|73|75|77) icon_name="wi-snow.svg";;
        80) icon_name="wi-day-showers.svg";;
        81|82) icon_name="wi-showers.svg";;
        85|86) icon_name="wi-day-snow.svg";;
        95) icon_name="wi-thunderstorm.svg";;
        96|99) icon_name="wi-storm-showers.svg";;
        *) icon_name="wi-na.svg";;
    esac
    echo "${icon_path}${icon_name}"
}

# Perth, Australia coordinates
LATITUDE="-31.9344"
LONGITUDE="115.8716"
TIMEZONE="Australia/Perth"

# API parameters
DAILY_VARS="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_hours"
FORECAST_DAYS="1"
API_URL="https://api.open-meteo.com/v1/forecast"

# Fetch weather data
weather_data=$(curl -s --get "$API_URL" \
    --data-urlencode "latitude=${LATITUDE}" \
    --data-urlencode "longitude=${LONGITUDE}" \
    --data-urlencode "daily=${DAILY_VARS}" \
    --data-urlencode "timezone=${TIMEZONE}" \
    --data-urlencode "forecast_days=${FORECAST_DAYS}")

# Check for empty response
if [ -z "$weather_data" ]; then
    echo "Error: Failed to fetch weather data." >&2
    exit 1
fi

# Check for error from API
if echo "$weather_data" | jq -e '.error' >/dev/null; then
    echo "Error from weather API:" >&2
    echo "$weather_data" | jq '.' >&2
    exit 1
fi

# Extract today's data
daily_data=$(echo "$weather_data" | jq '.daily')
weather_code=$(echo "$daily_data" | jq ".weather_code[0]")
temp_min=$(echo "$daily_data" | jq ".temperature_2m_min[0] | round")
temp_max=$(echo "$daily_data" | jq ".temperature_2m_max[0] | round")
precip_chance=$(echo "$daily_data" | jq ".precipitation_probability_max[0]")
precip_hours=$(echo "$daily_data" | jq ".precipitation_hours[0]")

# Get icon and convert to PNG for printing
weather_icon_path=$(get_weather_icon_path "$weather_code")
TMP_PNG=$(mktemp --suffix=.png)
trap 'rm -f "$TMP_PNG"' EXIT

# Convert SVG to PNG, rendering it at a larger size
# convert -background none -size 256x256 "$weather_icon_path" "$TMP_PNG"
convert -background white -density 900 "$weather_icon_path" -resize 256x256 "$TMP_PNG"

printf '\x1d\x21\x11'

echo
# Print the text summary
echo "${precip_chance}% (${precip_hours}h)"
echo "Min: ${temp_min}"
echo "Max: ${temp_max}"

# Print the image
./printimage.py "$TMP_PNG"

echo

date +"%dXX %b %Y" | sed -e 's/11XX/11th/' -e 's/12XX/12th/' -e 's/13XX/13th/' -e 's/1XX/1st/' -e 's/2XX/2nd/' -e 's/3XX/3rd/' -e 's/XX/th/'

printf '\x1d\x21\x00'

echo -e "\n\n\n"
