#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <base64.h>

#include <Test2_inferencing.h> // Edge Impulse model
#include "edge-impulse-sdk/dsp/image/image.hpp"

#define CAMERA_MODEL_XIAO_ESP32S3
#include "camera_pins.h"

// WiFi credentials
const char* ssid = "chaithu";
const char* password = "qwertyuiop";

// API details
const char* serverName = "http://192.168.59.150:5000/analyze";
const char* location = "Discovery Park K150";
const char* apiUsername = "admin";
const char* apiPassword = "password";

// Global state
bool debug_nn = false;
bool is_threat_active = false;
unsigned long detection_start_time = 0;
uint8_t *snapshot_buf = nullptr;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // Camera configuration
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_QVGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 10;
  config.fb_count = 2;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed");
    return;
  }

  Serial.println("Camera initialized");
}

void loop() {
  runInferenceAndSendIfThreat();
}

void runInferenceAndSendIfThreat() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  snapshot_buf = (uint8_t*)malloc(fb->width * fb->height * 3);
  if (!snapshot_buf) {
    Serial.println("Failed to allocate snapshot buffer");
    esp_camera_fb_return(fb);
    return;
  }

  if (!fmt2rgb888(fb->buf, fb->len, PIXFORMAT_JPEG, snapshot_buf)) {
    Serial.println("Failed to convert image");
    free(snapshot_buf);
    esp_camera_fb_return(fb);
    return;
  }

  ei::signal_t signal;
  signal.total_length = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
  signal.get_data = &ei_camera_get_data;

  // Resize image
  ei::image::processing::crop_and_interpolate_rgb888(
    snapshot_buf, fb->width, fb->height,
    snapshot_buf, EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);

  ei_impulse_result_t result = { 0 };
  EI_IMPULSE_ERROR err = run_classifier(&signal, &result, debug_nn);
  if (err != EI_IMPULSE_OK) {
    Serial.println("Failed to run classifier");
    free(snapshot_buf);
    esp_camera_fb_return(fb);
    return;
  }

  bool object_detected = false;

#if EI_CLASSIFIER_OBJECT_DETECTION == 1
  for (uint32_t i = 0; i < result.bounding_boxes_count; i++) {
    if (result.bounding_boxes[i].value > 0) {
      object_detected = true;
      break;
    }
  }
#endif

  unsigned long current_time = millis();
  if (object_detected) {
    if (!is_threat_active) {
      if (detection_start_time == 0) {
        detection_start_time = current_time;
      } else if ((current_time - detection_start_time) > 1000) {
        is_threat_active = true;
        Serial.println("Threat detected!");
        captureAndSendPhoto(fb); // Send only once when threat is active
      }
    }
  } else {
    detection_start_time = 0;
    is_threat_active = false;
    Serial.println("Safe.");
  }

  free(snapshot_buf);
  esp_camera_fb_return(fb);
}

void captureAndSendPhoto(camera_fb_t *fb) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return;
  }

  HTTPClient http;
  WiFiClient client;

  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  String contentType = "multipart/form-data; boundary=" + boundary;

  String bodyStart = "--" + boundary + "\r\n";
  bodyStart += "Content-Disposition: form-data; name=\"location\"\r\n\r\n";
  bodyStart += location;
  bodyStart += "\r\n--" + boundary + "\r\n";
  bodyStart += "Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n";
  bodyStart += "Content-Type: image/jpeg\r\n\r\n";

  String bodyEnd = "\r\n--" + boundary + "--\r\n";

  int totalLen = bodyStart.length() + fb->len + bodyEnd.length();
  uint8_t *fullBody = (uint8_t*) malloc(totalLen);
  if (!fullBody) {
    Serial.println("Failed to allocate memory for request body.");
    return;
  }

  memcpy(fullBody, bodyStart.c_str(), bodyStart.length());
  memcpy(fullBody + bodyStart.length(), fb->buf, fb->len);
  memcpy(fullBody + bodyStart.length() + fb->len, bodyEnd.c_str(), bodyEnd.length());

  http.begin(client, serverName);
  http.addHeader("Content-Type", contentType);

  // Basic Auth
  String authStr = String(apiUsername) + ":" + String(apiPassword);
  String authEncoded = base64::encode(authStr);
  http.addHeader("Authorization", "Basic " + authEncoded);

  int httpResponseCode = http.POST(fullBody, totalLen);
  if (httpResponseCode > 0) {
    Serial.printf("Image sent. Response: %d\n", httpResponseCode);
    Serial.println("Response: " + http.getString());
  } else {
    Serial.printf("Failed to connect. HTTP code: %d\n", httpResponseCode);
  }

  free(fullBody);
  http.end();
}

static int ei_camera_get_data(size_t offset, size_t length, float *out_ptr) {
  size_t pixel_ix = offset * 3;
  size_t out_ptr_ix = 0;
  size_t pixels_left = length;

  while (pixels_left--) {
    out_ptr[out_ptr_ix++] = (snapshot_buf[pixel_ix + 2] << 16) +
                            (snapshot_buf[pixel_ix + 1] << 8) +
                            snapshot_buf[pixel_ix];
    pixel_ix += 3;
  }

  return 0;
}
