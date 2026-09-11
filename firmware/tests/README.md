# Host checks

From the repository root on Linux, with a C11 compiler such as GCC installed:

```sh
sh firmware/tests/run-host.sh
```

The script works from any working directory, uses `cc` by default, and accepts a compiler executable through `CC`. It compiles with `-Wall -Wextra -Werror`, runs both test cases, and removes its own temporary executable. No ESP-IDF installation, downloaded headers, board or network connection is required.

On Windows, the same check can run through WSL with GCC installed. This PowerShell command was run successfully in the development checkout:

```powershell
wsl -e sh -lc 'cd /mnt/e/Dev/freecad/MicroDuckling && sh firmware/tests/run-host.sh'
```

Change the `/mnt/e/...` path to the location of your clone. A native Windows target build is not implied by this WSL command.

The tests compile the real `microduckling_io.c` against original, minimal declarations and fake peripheral calls in `stubs/` and `test_io.c`. These files are not copied or vendored ESP-IDF SDK headers. They check pin separation, reserved PSRAM pins, the explicit PWM bank/frequency, IMU bus selection, zero-duty startup, calibration and angle rejection, pulse conversion, and stopping configured outputs after initialization or write failures. The duty model stages a value separately from applying it, and injects failures in both `ledc_set_duty()` and `ledc_update_duty()`. The combined fade-service-dependent helper is deliberately absent from the test interface.

This check does **not** establish ESP-IDF API/ABI compatibility, real PWM timing, camera/PSRAM operation, reset voltage levels, or safe servo power behavior. An ESP-IDF target build and the hardware checks in [electronics.md](../../docs/electronics.md) remain separate requirements.
