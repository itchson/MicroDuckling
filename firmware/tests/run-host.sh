#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Compile the real I/O component against original host-only test doubles.
set -eu

test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
component_dir="$test_dir/../components/microduckling_io"
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/microduckling-io-host.XXXXXX")
cleanup() {
    rm -f "$build_dir/test_io"
    rmdir "$build_dir"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -I "$test_dir/stubs" -I "$component_dir/include" \
    "$component_dir/microduckling_io.c" "$test_dir/test_io.c" \
    -lm -o "$build_dir/test_io"
"$build_dir/test_io"
"$build_dir/test_io" partial
