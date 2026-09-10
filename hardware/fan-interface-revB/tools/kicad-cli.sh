#!/bin/sh
# Local Mac runtime, or the isolated Ubuntu/x570 runtime.
set -eu
pcb_mac_cli="$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
if [ -x "$pcb_mac_cli" ]; then
    exec "$pcb_mac_cli" "$@"
fi
if command -v kicad-cli >/dev/null 2>&1; then
    exec kicad-cli "$@"
fi
exec docker run --rm --network none --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$PWD,dst=/work" --workdir /work \
    --entrypoint kicad-cli \
    kicad/kicad@sha256:182c8005cb775a2c448a4c18681d489f1ff472a761885eba3e08b07e3c0564de \
    "$@"
