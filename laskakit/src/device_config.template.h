#ifndef DEVICE_CONFIG_H
#define DEVICE_CONFIG_H

/*
 * Device Configuration Template
 * 
 * SETUP INSTRUCTIONS:
 * 1. Copy this file to device_config.h
 * 2. Update all settings below for your specific device
 * 3. Add device_config.h to .gitignore to protect credentials
 */

// ========================================
// DEVICE IDENTITY CONFIGURATION
// ========================================
// IMPORTANT: Change these for each device to avoid conflicts
const char* DEVICE_ID = "CHANGE_ME_co2";           // Unique identifier (no spaces, lowercase)
const char* DEVICE_NAME = "CHANGE ME CO2 Sensor";  // Human-readable name for Home Assistant
const char* DEVICE_LOCATION = "CHANGE ME";         // Display text shown on OLED screen

// ========================================
// NETWORK CONFIGURATION
// ========================================
// WiFi credentials
const char* wifi_ssid = "YOUR_WIFI_SSID";
const char* wifi_password = "YOUR_WIFI_PASSWORD";

// ========================================
// MQTT BROKER CONFIGURATION
// ========================================
// MQTT server connection details
const char* mqtt_server = "192.168.1.100";      // Your MQTT broker IP
const int mqtt_port = 1883;
const char* mqtt_user = "your_mqtt_user";       // MQTT username
const char* mqtt_password = "your_mqtt_password"; // MQTT password

// ========================================
// SENSOR CONFIGURATION
// ========================================
// Data publishing interval (milliseconds)
const unsigned long PUBLISH_INTERVAL = 30000;  // 30 seconds

// Discovery message refresh intervals (milliseconds)
const unsigned long DISCOVERY_INTERVAL_STARTUP = 60000;   // 1 minute during first 10 minutes
const unsigned long DISCOVERY_INTERVAL_NORMAL = 300000;   // 5 minutes after startup

// ========================================
// HARDWARE CONFIGURATION
// ========================================
// These should not need to be changed for standard hardware setup
const int SDA_PIN = 33;           // I2C SDA pin
const int SCL_PIN = 32;           // I2C SCL pin  
const int POWER_PIN = 2;          // Power control pin
const int SCREEN_ADDRESS = 0x3C;  // OLED I2C address

#endif