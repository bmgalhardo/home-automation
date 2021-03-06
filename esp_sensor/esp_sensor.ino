#include "ESP8266WiFi.h"
#include "DHT.h"

/***********************
 Configurations
************************/

// Sensor Configurations
#define DHTPIN 2
#define DHTTYPE DHT11

// Network Configurations
const char* ssid = "MEO-B7EA35";
const char* password = "FYHE0QAG63T";

// Discovery Configurations
const char* location_name = "Hall";
const char* service_name = "DHT11";

// Consul Configuration
const char* consul_url = "192.168.8.101";
const int consul_port = 8500;
const char* consul_endpoint = "/v1/catalog/register";

DHT dht(DHTPIN, DHTTYPE);
WiFiServer server(80);

/**************************************
 * Message to send Consul to register ESP ip
 * This allows the ESPs to have dynamic ips
 * in the network, since Consul keeps track 
 * of the nodes available and their ips
 **************************************/
String prepareConsulPayload(String ip) {
  String payload, payloadHeader;
  payload = F("{\"Node\": \"ESP-");
  payload += location_name;
  payload += F("\", \"Address\": \"");
  payload += ip;
  payload += F(
    "\",\"NodeMeta\": {"
    "\"external-node\": \"true\","
    "\"external-probe\": \"true\""
    "},\"Service\": {\"Service\": \"");
  payload += service_name;
  payload += F(
    "\",\"Port\": 80}, \"Check\": {"
    "\"Name\": \"ESP health check\","     
    "\"status\": \"passing\","
    "\"Definition\": {"
    "\"TCP\": \"");
   payload += ip;
   payload += F(
    ":80\","
    "\"Interval\": \"60s\","
    "\"Timeout\": \"5s\""
    "}}}");
  
  payloadHeader = F(
    "PUT ");
  payloadHeader += consul_endpoint;
  payloadHeader += F(" HTTP/1.1\r\n"
    "Host:");
  payloadHeader += consul_url;
  payloadHeader += F(":");
  payloadHeader += consul_port;
  payloadHeader += F(
    "\r\n"
    "Content-Length: "
  );
  payloadHeader += payload.length();
  payloadHeader += F(
    "\r\n" 
    "Content-Type: application/json\r\n"
    "Connection: close\r\n"
    "\r\n"
  );
  Serial.println(payload);
  return payloadHeader + payload;
}
  
void setup() {
  
  Serial.begin(115200);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  String ip = WiFi.localIP().toString().c_str();
  server.begin();
  Serial.println("Web server started, ip: " + ip);
  dht.begin();

  // connect to consul and post payload
  WiFiClient client;

  if (client.connect(consul_url, consul_port)) {
    String content = prepareConsulPayload(ip);
    Serial.println("Connected to Consul, sending payload");
    //Serial.println(content);
    
    client.println(content);
    delay(500);

//    String response = "";
//    while (client.available()) {
//      char c = client.read();
//      response += c;
//    }
//
//    Serial.println(response);

    // close the connection:
    client.stop();
  }
}

// prepare a web page to be send to a client (web browser)
String prepareHtmlPage(float temperature, float humidity, float heat_index) {
  
  String htmlPage, htmlHeader;

  // body first to calculate lenght
  htmlPage = F(
    "# HELP iot_air_humidity_percent Air humidity, Percent.\n"
    "# TYPE iot_air_humidity_percent gauge\n"
    "iot_air_humidity_percent{location=\"");
  htmlPage += location_name;
  htmlPage += F("\"} ");
  htmlPage += humidity;
  htmlPage += F(
    "\n"
    "# HELP iot_air_temperature_celsius Air temperature, Celsius.\n"
    "# TYPE iot_air_temperature_celsius gauge\n"
    "iot_air_temperature_celsius{location=\"");
  htmlPage += location_name;
  htmlPage += F("\"} ");
  htmlPage += temperature;
  htmlPage += F(
    "\n"
    "# HELP iot_air_heat_index_celsius Apparent air temperature, based on temperature and humidity, Celsius.\n"
    "# TYPE iot_air_heat_index_celsius gauge\n"
    "iot_air_heat_index_celsius{location=\"");
  htmlPage += location_name;
  htmlPage += F("\"} ");
  htmlPage += temperature;
  htmlPage += F("\n");

  htmlHeader = F(
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/plain; version=0.0.4; charset=utf-8\r\n"
    "Content-Length: ");
  htmlHeader += htmlPage.length();
  htmlHeader += F(
    "\r\n"
    "Connection: close\r\n"  // the connection will be closed after completion of the response
    "\r\n");
    
  return htmlHeader + htmlPage;
}

void loop() {
  // Reading temperature or humidity takes about 250 milliseconds!
  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)
  float h = dht.readHumidity();
  // Read temperature as Celsius (the default)
  float t = dht.readTemperature();
  float hic = dht.computeHeatIndex(t, h, false);
    
  WiFiClient client = server.available();
  // wait for a client (web browser) to connect
  if (client) {
    while (client.connected()) {
      // read line by line what the client (web browser) is requesting
      if (client.available())
      {
        String line = client.readStringUntil('\r');
//        Serial.print(line);
        // wait for end of client's request, that is marked with an empty line
        if (line.length() == 1 && line[0] == '\n')
        {
          client.println(prepareHtmlPage(t, h, hic));
          break;
        }
      }
    }

    while (client.available()) {
      // wait for response to finish
      client.read();
    }

    // close the connection:
    client.stop();
  }
  delay(1000);
}
