idf_component_register(
    SRCS "microduckling_io.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_driver_ledc esp_driver_i2c espressif__esp32-camera
)
