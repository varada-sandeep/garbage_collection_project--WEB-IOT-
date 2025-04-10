/*
 * Garbage Bin Fill Level Monitoring System
 * NodeMCU Lolin V3 with Ultrasonic Sensor
 * 
 * This code reads data from an ultrasonic sensor, calculates the fill level of a garbage bin,
 * and sends this data to a remote server via HTTP POST requests.
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server API endpoint (replace with your public server URL)
const char* serverUrl = "http://your-server-domain.com/api/alert";

// Ultrasonic sensor pins
const int trigPin = D1;  // GPIO5
const int echoPin = D2;  // GPIO4

// Bin configuration
const char* binId = "BIN004";    // Unique ID for this bin
const int binHeight = 50;        // Height of the bin in cm

// Timing configuration
const unsigned long sendInterval = 3600000;  // Send data every hour (in milliseconds)
unsigned long previousMillis = 0;

// Connection retry configuration
const int maxRetries = 5;
const unsigned long retryDelay = 30000;  // 30 seconds between retries

void setup() {
  // Initialize Serial
  Serial.begin(115200);
  Serial.println("\nGarbage Bin Fill Level Monitoring System");
  
  // Initialize ultrasonic sensor pins
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  // Connect to WiFi
  connectToWiFi();
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Check if it's time to send data
  if (currentMillis - previousMillis >= sendInterval) {
    previousMillis = currentMillis;
    
    // Measure fill level
    int fillLevel = measureFillLevel();
    
    // Send data to server
    sendDataToServer(fillLevel);
  }
  
  // Check WiFi connection and reconnect if needed
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection lost. Reconnecting...");
    connectToWiFi();
  }
  
  // Small delay to prevent CPU hogging
  delay(100);
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi network: ");
  Serial.println(ssid);
  
  // Begin WiFi connection
  WiFi.begin(ssid, password);
  
  // Wait for connection with timeout
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected successfully!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi. Will retry later.");
  }
}

int measureFillLevel() {
  // Take multiple readings and average them for stability
  const int numReadings = 5;
  long totalDistance = 0;
  
  for (int i = 0; i < numReadings; i++) {
    // Clear the trigPin
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    
    // Set the trigPin on HIGH state for 10 microseconds
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    // Read the echoPin, returns the sound wave travel time in microseconds
    long duration = pulseIn(echoPin, HIGH, 30000); // Timeout after 30ms
    
    // Calculate the distance in centimeters
    // Speed of sound is 343 m/s or 0.0343 cm/µs
    // Time is divided by 2 because sound travels to the object and back
    long distance = (duration * 0.0343) / 2;
    
    // Filter extreme values
    if (distance > 0 && distance <= binHeight) {
      totalDistance += distance;
    } else {
      // If reading is invalid, try again
      i--;
      delay(50);
    }
    
    delay(100);  // Small delay between readings
  }
  
  // Calculate average distance
  int avgDistance = totalDistance / numReadings;
  
  // Calculate fill level as a percentage
  // When distance is small (bin full), fill level is high
  int fillLevel = 100 - ((avgDistance * 100) / binHeight);
  
  // Constrain the fill level between 0 and 100
  fillLevel = constrain(fillLevel, 0, 100);
  
  Serial.print("Current fill level: ");
  Serial.print(fillLevel);
  Serial.println("%");
  
  return fillLevel;
}

void sendDataToServer(int fillLevel) {
  // Check if WiFi is connected
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Cannot send data.");
    return;
  }
  
  Serial.println("Sending data to server...");
  
  WiFiClient client;
  HTTPClient http;
  
  // Start HTTP connection
  http.begin(client, serverUrl);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON document
  StaticJsonDocument<200> jsonDoc;
  jsonDoc["bin_id"] = binId;
  jsonDoc["fill_level"] = fillLevel;
  
  // Serialize JSON to string
  String jsonStr;
  serializeJson(jsonDoc, jsonStr);
  
  // Send the POST request
  int retryCount = 0;
  int httpResponseCode;
  bool success = false;
  
  while (!success && retryCount < maxRetries) {
    httpResponseCode = http.POST(jsonStr);
    
    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
      String response = http.getString();
      Serial.println("Server response: " + response);
      
      // Check if response is successful
      if (httpResponseCode == 200) {
        Serial.println("Data sent successfully!");
        success = true;
      } else {
        Serial.println("Server error. Retrying...");
        retryCount++;
        delay(retryDelay);
      }
    } else {
      Serial.print("Error on sending POST: ");
      Serial.println(http.errorToString(httpResponseCode));
      retryCount++;
      
      // Wait before retrying
      Serial.print("Retry attempt ");
      Serial.print(retryCount);
      Serial.print(" of ");
      Serial.print(maxRetries);
      Serial.println(" in 30 seconds...");
      delay(retryDelay);
    }
  }
  
  // End HTTP connection
  http.end();
  
  if (!success) {
    Serial.println("Failed to send data after maximum retries.");
  }
}
