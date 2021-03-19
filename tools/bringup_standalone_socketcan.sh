# in standalone mode, enable passthrough -> socketcan
# set $DEVICE to your tty endpoint
# ..then execute this script
DEVICE=ttyUSB1

sudo modprobe can
sudo modprobe can-raw
sudo modprobe slcan

sudo slcand -o -s6 -S 1000000 /dev/$DEVICE
sudo ip link set up slcan0

