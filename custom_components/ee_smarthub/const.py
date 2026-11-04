"""Constants for the EE SmartHub integration."""

from datetime import timedelta

DOMAIN = "ee_smarthub"

DEFAULT_HOST = "192.168.1.1"
DEFAULT_SCAN_INTERVAL = 30

# WiFi devices flap `active` due to power saving, so keep them home this long.
CONSIDER_HOME_INTERVAL = timedelta(minutes=10)
