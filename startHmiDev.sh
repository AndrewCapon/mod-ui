source modui-env/bin/activate
export MOD_DEV_ENVIRONMENT=0
export MOD_HARDWARE_DESC_FILE=./mod-hardware-descriptor.json
export MOD_LOG=1
export MOD_EXTENDED_LOG=1
export MOD_DEV_ENVIRONMENT=0
export MOD_DEV_EMULATE_HMI=0
export MOD_ENABLE_MULTIPLE_CONTROLLERS=1
export MOD_HMI_SERIAL_PORT=/dev/tnt2
python3 ./server.py

