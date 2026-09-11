// SPDX-License-Identifier: Apache-2.0
// Original minimal host-test model; not an ESP-IDF SDK header or hardware driver.
#pragma once
#include <stdbool.h>
#include "esp_err.h"
typedef void* i2c_master_bus_handle_t;
enum { I2C_NUM_1=1, I2C_CLK_SRC_DEFAULT=0 };
typedef struct {int i2c_port,sda_io_num,scl_io_num,clk_source,glitch_ignore_cnt;struct {bool enable_internal_pullup;}flags;}i2c_master_bus_config_t;
esp_err_t i2c_new_master_bus(const i2c_master_bus_config_t*,i2c_master_bus_handle_t*);
