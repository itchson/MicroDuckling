// SPDX-License-Identifier: Apache-2.0
#include "microduckling_io.h"
#include <math.h>
#include <stdbool.h>
#include <string.h>
#include "driver/ledc.h"
#include "sdkconfig.h"

#if !CONFIG_IDF_TARGET_ESP32
#error "This pin map and high-speed LEDC bank require classic ESP32, not ESP32-S3/C3."
#endif
#if !CONFIG_SPIRAM
#error "Enable PSRAM for the selected ESP32-CAM configuration."
#endif
#if !CONFIG_SCCB_HARDWARE_I2C_PORT0 || !CONFIG_SCCB_HARDWARE_I2C_DRIVER_NEW
#error "Select camera SCCB I2C0 and the new I2C driver; I2C1 is reserved for the IMU."
#endif
#if !CONFIG_ESP_CONSOLE_NONE || !CONFIG_BOOTLOADER_LOG_LEVEL_NONE
#error "Disable the UART console and bootloader logs before reusing GPIO1/3 for the IMU."
#endif

#define SERVO_MODE LEDC_HIGH_SPEED_MODE
#define SERVO_TIMER LEDC_TIMER_0
#define SERVO_HZ 50U
#define SERVO_STEPS 65536U
#define HIP_LIMIT 0.20943951023931953f
#define NECK_LIMIT 0.7853981633974483f
static const int pins[MD_SERVO_COUNT] = {
    MD_LEFT_HIP_GPIO, MD_RIGHT_HIP_GPIO, MD_NECK_GPIO, MD_JAW_GPIO
};
static const float lower[MD_SERVO_COUNT] = {-HIP_LIMIT, -HIP_LIMIT, -NECK_LIMIT, 0};
static const float upper[MD_SERVO_COUNT] = { HIP_LIMIT,  HIP_LIMIT,  NECK_LIMIT, HIP_LIMIT};
static md_servo_calibration_t cal[MD_SERVO_COUNT];
static unsigned configured_channels;
static bool ready;

camera_config_t md_camera_config(void)
{
    return (camera_config_t) {
        .pin_pwdn = 32, .pin_reset = -1, .pin_xclk = 0,
        .pin_sccb_sda = 26, .pin_sccb_scl = 27,
        .pin_d0 = 5, .pin_d1 = 18, .pin_d2 = 19, .pin_d3 = 21,
        .pin_d4 = 36, .pin_d5 = 39, .pin_d6 = 34, .pin_d7 = 35,
        .pin_vsync = 25, .pin_href = 23, .pin_pclk = 22,
        .xclk_freq_hz = 20000000,
        .ledc_timer = LEDC_TIMER_0, .ledc_channel = LEDC_CHANNEL_0,
        .pixel_format = PIXFORMAT_JPEG, .frame_size = FRAMESIZE_QVGA,
        .jpeg_quality = 12, .fb_count = 1,
        .fb_location = CAMERA_FB_IN_PSRAM, .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
    };
}

esp_err_t md_imu_bus_init(i2c_master_bus_handle_t *bus)
{
    if (!bus) return ESP_ERR_INVALID_ARG;
    const i2c_master_bus_config_t config = {
        .i2c_port = I2C_NUM_1, .sda_io_num = MD_IMU_SDA_GPIO,
        .scl_io_num = MD_IMU_SCL_GPIO, .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7, .flags.enable_internal_pullup = false,
    };
    // Use the breakout's external pull-ups to 3.3 V. Sensor driver is separate.
    return i2c_new_master_bus(&config, bus);
}

esp_err_t md_servos_stop(void)
{
    esp_err_t result = ESP_OK;
    for (unsigned i = 0; i < configured_channels; ++i) {
        const esp_err_t err = ledc_stop(SERVO_MODE, (ledc_channel_t)i, 0);
        if (err != ESP_OK) result = err;
    }
    return result;
}

esp_err_t md_servos_init(const md_servo_calibration_t calibration[MD_SERVO_COUNT])
{
    if (ready || configured_channels) return ESP_ERR_INVALID_STATE;
    if (!calibration) return ESP_ERR_INVALID_ARG;
    for (unsigned i = 0; i < MD_SERVO_COUNT; ++i) {
        const md_servo_calibration_t *c = &calibration[i];
        if (!isfinite(c->neutral_us) || !isfinite(c->us_per_rad) || c->us_per_rad == 0 ||
            c->min_pulse_us < 500 || c->max_pulse_us > 2500 || c->min_pulse_us >= c->max_pulse_us)
            return ESP_ERR_INVALID_ARG;
        const float a = c->neutral_us + lower[i] * c->us_per_rad;
        const float b = c->neutral_us + upper[i] * c->us_per_rad;
        if (!isfinite(a) || !isfinite(b) || fminf(a, b) < c->min_pulse_us || fmaxf(a, b) > c->max_pulse_us)
            return ESP_ERR_INVALID_ARG;
    }
    const ledc_timer_config_t timer = {
        .speed_mode = SERVO_MODE, .duty_resolution = LEDC_TIMER_16_BIT,
        .timer_num = SERVO_TIMER, .freq_hz = SERVO_HZ, .clk_cfg = LEDC_USE_APB_CLK,
    };
    esp_err_t err = ledc_timer_config(&timer);
    if (err != ESP_OK) return err;
    for (unsigned i = 0; i < MD_SERVO_COUNT; ++i) {
        const ledc_channel_config_t channel = {
            .gpio_num = pins[i], .speed_mode = SERVO_MODE, .channel = (ledc_channel_t)i,
            .intr_type = LEDC_INTR_DISABLE, .timer_sel = SERVO_TIMER, .duty = 0, .hpoint = 0,
        };
        err = ledc_channel_config(&channel);
        if (err != ESP_OK) { md_servos_stop(); return err; }
        configured_channels++;
    }
    memcpy(cal, calibration, sizeof(cal));
    ready = true;
    return ESP_OK;
}

esp_err_t md_servos_write(const float radians[MD_SERVO_COUNT])
{
    if (!ready) return ESP_ERR_INVALID_STATE;
    if (!radians) return ESP_ERR_INVALID_ARG;
    uint32_t duties[MD_SERVO_COUNT];
    // Validate the complete command before writing any channel.
    for (unsigned i = 0; i < MD_SERVO_COUNT; ++i) {
        if (!isfinite(radians[i]) || radians[i] < lower[i] || radians[i] > upper[i])
            return ESP_ERR_INVALID_ARG;
        const float us = cal[i].neutral_us + radians[i] * cal[i].us_per_rad;
        if (!isfinite(us) || us < cal[i].min_pulse_us || us > cal[i].max_pulse_us)
            return ESP_ERR_INVALID_ARG;
        duties[i] = (uint32_t)lroundf(us * (SERVO_STEPS * SERVO_HZ / 1000000.0f));
    }
    for (unsigned i = 0; i < MD_SERVO_COUNT; ++i) {
        // This API has one owning control task. The combined thread-safe IDF
        // helper requires the fade service, which this component does not use.
        esp_err_t err = ledc_set_duty(SERVO_MODE, (ledc_channel_t)i, duties[i]);
        if (err != ESP_OK) { md_servos_stop(); return err; }
        err = ledc_update_duty(SERVO_MODE, (ledc_channel_t)i);
        if (err != ESP_OK) { md_servos_stop(); return err; }
    }
    return ESP_OK;
}
