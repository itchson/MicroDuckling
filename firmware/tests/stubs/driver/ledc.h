// SPDX-License-Identifier: Apache-2.0
// Original minimal host-test model; not an ESP-IDF SDK header or hardware driver.
#pragma once
#include <stdint.h>
#include "esp_err.h"
typedef int ledc_channel_t;
enum { LEDC_HIGH_SPEED_MODE, LEDC_LOW_SPEED_MODE, LEDC_TIMER_0=0, LEDC_CHANNEL_0=0,
       LEDC_TIMER_16_BIT=16, LEDC_USE_APB_CLK=1, LEDC_INTR_DISABLE=0 };
typedef struct {int speed_mode,duty_resolution,timer_num;unsigned freq_hz;int clk_cfg;} ledc_timer_config_t;
typedef struct {int gpio_num,speed_mode,channel,intr_type,timer_sel;uint32_t duty,hpoint;} ledc_channel_config_t;
esp_err_t ledc_timer_config(const ledc_timer_config_t*);
esp_err_t ledc_channel_config(const ledc_channel_config_t*);
esp_err_t ledc_stop(int,ledc_channel_t,int);
esp_err_t ledc_set_duty(int,ledc_channel_t,uint32_t);
esp_err_t ledc_update_duty(int,ledc_channel_t);
