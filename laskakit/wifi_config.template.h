#ifndef WIFI_CONFIG_H
#define WIFI_CONFIG_H

// WiFi Configuration - Edit these values for your network
const char* wifi_ssid = "your_wifi_network";        // ← Change this to your WiFi name
const char* wifi_password = "your_wifi_password";   // ← Change this to your WiFi password

// MQTT Configuration - Edit these for your Home Assistant setup
const char* mqtt_server = "homeassistant.local";    // Home Assistant IP or hostname
const int mqtt_port = 1883;
const char* mqtt_user = "";                         // MQTT username (if authentication enabled)
const char* mqtt_password = "";                     // MQTT password (if authentication enabled)

// Device Configuration - Customize your device identity
const char* device_id = "esplan_co2_sensor";        // Unique device identifier
const char* device_name = "ESPlan CO2 Sensor";      // Display name in Home Assistant

#endif