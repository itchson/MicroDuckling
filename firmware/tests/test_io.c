// SPDX-License-Identifier: Apache-2.0
// Original minimal host-test model; not an ESP-IDF SDK header or hardware driver.
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "microduckling_io.h"
static unsigned channels,writes,updates,stops;
static int fail_channel=-1,fail_write=-1,fail_update=-1;
static uint32_t duty[4],pending_duty[4];
esp_err_t ledc_timer_config(const ledc_timer_config_t*c){assert(c->speed_mode==LEDC_HIGH_SPEED_MODE);assert(c->freq_hz==50&&c->duty_resolution==16&&c->timer_num==0&&c->clk_cfg==LEDC_USE_APB_CLK);return ESP_OK;}
esp_err_t ledc_channel_config(const ledc_channel_config_t*c){const int gpio[]={2,13,14,15};assert(c->gpio_num==gpio[c->channel]);assert(c->speed_mode==LEDC_HIGH_SPEED_MODE&&c->timer_sel==0&&c->duty==0);if(c->channel==fail_channel)return ESP_FAIL;channels++;return ESP_OK;}
esp_err_t ledc_stop(int mode,ledc_channel_t c,int idle){assert(mode==LEDC_HIGH_SPEED_MODE&&idle==0);duty[c]=0;stops++;return ESP_OK;}
esp_err_t ledc_set_duty(int mode,ledc_channel_t c,uint32_t value){assert(mode==LEDC_HIGH_SPEED_MODE);writes++;if(c==fail_write)return ESP_FAIL;pending_duty[c]=value;return ESP_OK;}
esp_err_t ledc_update_duty(int mode,ledc_channel_t c){assert(mode==LEDC_HIGH_SPEED_MODE);updates++;if(c==fail_update)return ESP_FAIL;duty[c]=pending_duty[c];return ESP_OK;}
esp_err_t i2c_new_master_bus(const i2c_master_bus_config_t*c,i2c_master_bus_handle_t*b){assert(c->i2c_port==1&&c->sda_io_num==3&&c->scl_io_num==1&&!c->flags.enable_internal_pullup);*b=(void*)1;return ESP_OK;}
int main(int argc,char**argv){
 md_servo_calibration_t calibration[4];for(int i=0;i<4;i++)calibration[i]=(md_servo_calibration_t){1500,500,1000,2000};
 float angles[4]={0,0,0,0};
 assert(md_servos_write(angles)==ESP_ERR_INVALID_STATE);assert(md_servos_init(NULL)==ESP_ERR_INVALID_ARG);
 calibration[0].us_per_rad=NAN;assert(md_servos_init(calibration)==ESP_ERR_INVALID_ARG);calibration[0].us_per_rad=500;
 calibration[2].max_pulse_us=1600;assert(md_servos_init(calibration)==ESP_ERR_INVALID_ARG);calibration[2].max_pulse_us=2000;
 camera_config_t camera=md_camera_config();assert(camera.pin_xclk==0&&camera.ledc_timer==0&&camera.ledc_channel==0&&camera.fb_location==CAMERA_FB_IN_PSRAM);
 const int camera_pins[]={camera.pin_xclk,camera.pin_pwdn,camera.pin_sccb_sda,camera.pin_sccb_scl,camera.pin_d0,camera.pin_d1,camera.pin_d2,camera.pin_d3,camera.pin_d4,camera.pin_d5,camera.pin_d6,camera.pin_d7,camera.pin_vsync,camera.pin_href,camera.pin_pclk};
 const int allocated[]={2,13,14,15,3,1};for(unsigned i=0;i<sizeof(allocated)/sizeof(*allocated);i++){assert(allocated[i]!=12&&allocated[i]!=16&&allocated[i]!=17);for(unsigned j=0;j<sizeof(camera_pins)/sizeof(*camera_pins);j++)assert(allocated[i]!=camera_pins[j]);}
 i2c_master_bus_handle_t bus=NULL;assert(md_imu_bus_init(NULL)==ESP_ERR_INVALID_ARG);assert(md_imu_bus_init(&bus)==ESP_OK&&bus);
 if(argc>1&&strcmp(argv[1],"partial")==0){fail_channel=2;assert(md_servos_init(calibration)==ESP_FAIL);assert(channels==2&&stops==2);assert(md_servos_write(angles)==ESP_ERR_INVALID_STATE);puts("Partial-init failure stops every configured output.");return 0;}
 assert(md_servos_init(calibration)==ESP_OK&&channels==4&&writes==0&&updates==0);assert(md_servos_init(calibration)==ESP_ERR_INVALID_STATE);
 assert(md_servos_write(angles)==ESP_OK&&writes==4&&updates==4);for(int i=0;i<4;i++)assert(duty[i]==4915);
 angles[0]=.22f;assert(md_servos_write(angles)==ESP_ERR_INVALID_ARG&&writes==4&&updates==4);angles[0]=0;
 angles[3]=-.01f;assert(md_servos_write(angles)==ESP_ERR_INVALID_ARG&&writes==4&&updates==4);angles[3]=0;
 angles[2]=NAN;assert(md_servos_write(angles)==ESP_ERR_INVALID_ARG&&writes==4&&updates==4);angles[2]=0;
 angles[0]=.1f;angles[1]=-.1f;assert(md_servos_write(angles)==ESP_OK&&duty[0]>4915&&duty[1]<4915);
 // A staging failure must not issue an update for that channel or touch later ones.
 unsigned before_writes=writes,before_updates=updates;
 fail_write=2;assert(md_servos_write(angles)==ESP_FAIL&&stops==4);
 assert(writes==before_writes+3&&updates==before_updates+2);for(int i=0;i<4;i++)assert(duty[i]==0);
 // Recovery requires a new explicit command from the owning control task.
 fail_write=-1;assert(md_servos_write(angles)==ESP_OK);for(int i=0;i<4;i++)assert(duty[i]>0);
 before_writes=writes;before_updates=updates;
 fail_update=1;assert(md_servos_write(angles)==ESP_FAIL&&stops==8);
 assert(writes==before_writes+2&&updates==before_updates+2);for(int i=0;i<4;i++)assert(duty[i]==0);
 puts("Pin separation, explicit timer bank, bus assignment, calibration, angle bounds, conversion and separate set/update failure-stop checks passed.");return 0;
}
