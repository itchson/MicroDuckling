// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <stdint.h>
#include "esp_camera.h"
#include "esp_err.h"
#include "driver/i2c_master.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { MD_LEFT_HIP, MD_RIGHT_HIP, MD_NECK_YAW, MD_JAW_PITCH, MD_SERVO_COUNT };
enum { MD_LEFT_HIP_GPIO = 2, MD_RIGHT_HIP_GPIO = 13, MD_NECK_GPIO = 14,
       MD_JAW_GPIO = 15, MD_IMU_SDA_GPIO = 3, MD_IMU_SCL_GPIO = 1 };

// Measured per servo and installed horn; no unverified calibration is supplied.
typedef struct {
    float neutral_us;
    float us_per_rad; // Signed: reverses the installed servo direction when negative.
    uint16_t min_pulse_us;
    uint16_t max_pulse_us;
} md_servo_calibration_t;

// Classic Ai-Thinker ESP32-CAM / OV2640, camera low-speed LEDC0, PSRAM frame buffer.
camera_config_t md_camera_config(void);
// Owns I2C1. Camera must use I2C0; UART and microSD must remain disabled.
esp_err_t md_imu_bus_init(i2c_master_bus_handle_t *bus);
// Configure four high-speed 50 Hz outputs with zero duty (no pulses).
// Call all servo functions from one control task. Reinitialization is rejected.
esp_err_t md_servos_init(const md_servo_calibration_t calibration[MD_SERVO_COUNT]);
// Radians: left/right ±12°, neck ±45°, jaw 0..12°. Invalid sets are rejected.
esp_err_t md_servos_write(const float radians[MD_SERVO_COUNT]);
// Stops PWM at logic low. This is not a physical servo-power disconnect.
esp_err_t md_servos_stop(void);

#ifdef __cplusplus
}
#endif
