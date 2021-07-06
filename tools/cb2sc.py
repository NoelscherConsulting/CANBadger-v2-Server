#####################################################################################
# CanBadger SocketCan Bridge                                                        #
# Copyright (c) 2021 Noelscher Consulting GmbH                                      #
#                                                                                   #
# Permission is hereby granted, free of charge, to any person obtaining a copy      #
# of this software and associated documentation files (the "Software"), to deal     #
# in the Software without restriction, including without limitation the rights      #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell         #
# copies of the Software, and to permit persons to whom the Software is             #
# furnished to do so, subject to the following conditions:                          #
#                                                                                   #
# The above copyright notice and this permission notice shall be included in        #
# all copies or substantial portions of the Software.                               #
#                                                                                   #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR        #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,          #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE       #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER            #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,     #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN         #
# THE SOFTWARE.                                                                     #
#####################################################################################

from libcanbadger import EthernetMessage, EthernetMessageType, ActionType, CANBadger
from libcanbadger.util import CANBadgerSettings, CanbadgerStatusBits

import argparse
import logging
import ipaddress
import can
import struct

unpack_unpack_can_header = struct.Struct('>BIIIB').unpack


def main():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description='CANBadger to SocketCAN Service.')
    parser.add_argument('--ip', dest='ip', type=str, default=None,
                        help='CANBadger IP Address')
    parser.add_argument('--cb-id', dest='cb_id', type=str, default=None,
                        help='Target CANBadger ID. Please specify either IP or ID. '
                             'If both are specified, only IP is considered.')
    parser.add_argument('--cb-interface', dest='iface_num', type=str, default='1',
                        help='Choose which CANBadger Interface to use: 1 or 2. You can also specify both: 1,2 but'
                             'then you also have to specify two socketcan interfaces. Default: 1')
    parser.add_argument('--host-interface', dest='host_iface', type=str, default='vcan0', required=True,
                        help='Choose which socketcan interface to use on the host. If using both CANBadger interfaces, '
                             'specify two interfaces like this: vcan0,vcan1 (for interface 1 and 2, respectively)')
    parser.add_argument('--rx-only', dest='rx_only', type=bool, default=False,
                        help='Disables forwarding messages back to the canbadger from socketcan interface')
    parser.add_argument('--can1-speed', dest='can1_speed', type=int, choices=[10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000],
                        help='Sets CANBadger CAN1 speed to the given value.')
    parser.add_argument('--can2-speed', dest='can2_speed', type=int, choices=[10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000],
                        help='Sets CANBadger CAN2 speed to the given value.')

    args = parser.parse_args()

    if not args.ip and not args.cb_id:
        print("CANBadger IP or ID is required!")
        parser.print_help()
        exit(-1)

    cb_ip = None
    cb_id = None
    if args.ip:
        cb_ip = args.ip
    else:
        cb_id = args.cb_id

    # validate other settings here
    if cb_ip:
        # try to parse it
        cb_ip = ipaddress.ip_address(cb_ip)

    iface_num = 1
    if args.iface_num:
        iface_num = int(iface_num)

    can_speed = 500000
    if (iface_num == 1 and not args.can1_speed) or (iface_num == 2 and not args.can2_speed):
        logging.warning(f"Using default can speed for CanBadger interface {iface_num}: {can_speed}")
    else:
        can_speed = args.can1_speed if iface_num == 1 else args.can2_speed

    # if no IP:
    # determine IP by ID broadcast TODO

    # print full configuration
    logging.info("# Configuration Summary")
    logging.info(f"Connecting to CanBadger: {cb_ip if cb_ip else cb_id}")
    logging.info(f"Connecting to SocketCan Interface: {args.host_iface}")
    logging.info("#")
    if args.rx_only:
        logging.info("Disabling transmission (rx only mode)")

    # start!
    cb_ip = str(cb_ip)

    # connecting
    cb = CANBadger(cb_ip)
    logging.info("Connecting to CANBadger..")
    connected = cb.connect()

    if connected:
        logging.info("Connected successfully!")
    else:
        logging.error("Failed to connect. Exiting.")
        return
    cb.stop()

    # setup
    settings = CANBadgerSettings()
    if iface_num == 1:
        settings.set_status_bit(CanbadgerStatusBits.CAN1_LOGGING)
        settings.set_status_bit(CanbadgerStatusBits.CAN1_STANDARD)
        settings.can1_speed = can_speed
    else:
        settings.set_status_bit(CanbadgerStatusBits.CAN2_LOGGING)
        settings.set_status_bit(CanbadgerStatusBits.CAN2_STANDARD)
        settings.can2_speed = can_speed
    settings.spi_speed = 20000000
    cb.configure(settings)

    cb.start()

    # open the sockertcan interface
    bus = can.interface.Bus(channel=args.host_iface, bustype='socketcan')

    try:
        while True:
            # receive from canbadger
            msg_from_cb = cb.receive()
            if msg_from_cb != -1:
                logging.info("received something from cb!")
                if msg_from_cb.msg_type == EthernetMessageType.DATA:
                    pbyte, _, frame_id, _, length = unpack_unpack_can_header(msg_from_cb.data[:14])
                    frame_payload = msg_from_cb.data[14:14 + length]
                    is_extended = True if pbyte & 0x20 > 0 else False

                    msg = can.Message(arbitration_id=frame_id,
                                      data=frame_payload,
                                      is_extended_id=is_extended)
                    bus.send(msg)

            # receive from socketcan
            msg_from_sc = bus.recv(timeout=0.0)  # non-blocking read
            if msg_from_sc is not None:
                logging.info("got from socketcan.")
                # parse the msg TODO

                bin_iface = struct.pack('B', iface_num)
                bin_arbid = struct.pack('I', msg_from_sc.arbitration_id)
                # f = struct.pack('>BI', interface_num, in_arb_id)
                f = bin_iface + bin_arbid
                f += msg_from_sc.data
                eth_msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.START_REPLAY, len(f), f)
                cb.send(eth_msg)

    except KeyboardInterrupt:
        cb.stop()
        cb.shutdown_connection()


if __name__=='__main__':
    main()
