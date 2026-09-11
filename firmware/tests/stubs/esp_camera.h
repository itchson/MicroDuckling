// SPDX-License-Identifier: Apache-2.0
// Original minimal host-test model; not an ESP-IDF SDK header or hardware driver.
#pragma once
#include "driver/ledc.h"
enum {PIXFORMAT_JPEG=1,FRAMESIZE_QVGA=1,CAMERA_FB_IN_PSRAM=1,CAMERA_GRAB_WHEN_EMPTY=0};
typedef struct {
 int pin_pwdn,pin_reset,pin_xclk,pin_sccb_sda,pin_sccb_scl;
 int pin_d0,pin_d1,pin_d2,pin_d3,pin_d4,pin_d5,pin_d6,pin_d7;
 int pin_vsync,pin_href,pin_pclk,xclk_freq_hz,ledc_timer,ledc_channel;
 int pixel_format,frame_size,jpeg_quality,fb_count,fb_location,grab_mode;
} camera_config_t;
