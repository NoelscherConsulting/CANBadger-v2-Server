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

from canbadger_messages import StartUdsMessage, UdsResponse, EthernetMessage, EthernetMessageType, ActionType
from helpers import CanParser
import argparse
import logging
import ipaddress
import socket
import can
import struct
import random
from multiprocessing import Process, Queue


def process_canbadger(cb_ip, cb_aport, host_ip, host_port, interface_num, in_queue, out_queue):
    parser = CanParser()
    cb_ip = str(cb_ip)
    host_ip = str(host_ip)
    # cb_aport should be 13371
    # at this point, we're connected to the cb already
    # create the socket, start logging

    logging.info("Connecting to CANBadger..")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if not host_port:
        host_port = random.randint(15000, 25000)
    sock.bind((host_ip, host_port))
    sock.sendto(b'\x04' + b'\x00' + struct.pack('<I', 4) + struct.pack('<I', host_port) + b'\x00',
                (cb_ip, cb_aport)) # connect port is hard-coded to this value

    # wait for ack
    ack, _ = sock.recvfrom(255)
    if EthernetMessage.unserialize(ack).msg_type == EthernetMessageType.ACK:
        logging.info("Connected successfully!")
    else:
        logging.error("Failed to connect: invalid response received. Exiting.")
        return

    sock.setblocking(False)
    start_msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.LOG_RAW_CAN_TRAFFIC, 0, b'')
    sock.sendto(start_msg.serialize(), (cb_ip, cb_aport))

    abort = False
    while not abort:
        # send frames to the CB from in_queue
        while in_queue.qsize() > 0:
            in_msg = in_queue.get()
            payload = in_msg['payload']
            in_arb_id = in_msg['id']

            bin_iface = struct.pack('B', interface_num)
            bin_arbid = struct.pack('I', in_arb_id)
            #f = struct.pack('>BI', interface_num, in_arb_id)
            f = bin_iface + bin_arbid
            f += payload
            eth_msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.START_REPLAY, len(f), f)
            sock.sendto(eth_msg.serialize(), (cb_ip, cb_aport))

        # put frames received from CB into out_queue
        try:
            rx_message, _ = sock.recvfrom(255)
        except BlockingIOError:
            continue
        rx_eth_message = EthernetMessage.unserialize(rx_message, unpack_data=True)
        if rx_eth_message.msg_type == EthernetMessageType.DATA:
            frame = parser.parseToCanFrame(rx_eth_message.data)
            out_queue.put({
                'id': frame.frame_id,
                'payload': frame.frame_payload,
                'is_extended': frame.is_extended(),
            })


def process_socketcan(interface, in_queue, out_queue):
    # open the sockertcan interface
    bus = can.interface.Bus(channel=interface, bustype='socketcan')
    abort = False
    while not abort:
        # send frames to socketcan from in_queue
        while in_queue.qsize() > 0:
            in_msg = in_queue.get()
            # we just pass dicts around for now
            msg = can.Message(arbitration_id=in_msg['id'],
                              data=in_msg['payload'],
                              is_extended_id=in_msg['is_extended'])
            bus.send(msg)

        out_msg = bus.recv(timeout=0.0) # non-blocking read
        while out_msg is not None:
            # parse the msg TODO
            out_q_message = { 'id': out_msg.arbitration_id, 'payload': out_msg.data }
            out_queue.put(out_q_message)
            out_msg = bus.recv(timeout=0.0)

def main():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description='CANBadger to SocketCAN Service.')
    parser.add_argument('--ip', dest='ip', type=str, default=None,
                        help='CANBadgers IP Address')
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
    parser.add_argument('--listen-ip', dest='host_ip', type=str, default=None,
                        help='Host IP address to listen on. '
                             'By default, we listen on 0.0.0.0 - ipv6 is not supported')
    parser.add_argument('--listen-port', dest='host_port', type=int, default=None,
                        help='Host UDP Port to listen on. '
                             'By default, we choose a random port')

    args = parser.parse_args()

    if not args.ip:
        print("CANBadger IP is required!")
        parser.print_help()
        exit(-1)

    cb_ip = args.ip
    # try to parse it
    cb_ip = ipaddress.ip_address(cb_ip)

    # validate other settings here
    host_ip = ipaddress.ip_address('0.0.0.0')
    if args.host_ip:
        host_ip = ipaddress.ip_address(args.host_ip)
    host_port = random.randint(10000, 15000)
    if args.host_port:
        host_port = args.host_port

    iface_num = 1
    dual_interface_mode = False
    host_interface = ['']
    if args.host_iface:
        host_interface = [args.host_iface]
    else:
        print("Host interface is required!")
        parser.print_help()
        exit(-1)


    if args.iface_num:
        # check if we want two interfaces
        if_split = args.iface_num.split(',')
        if len(if_split) > 1:
            dual_interface_mode = True
            # check host interfaces
            hif_split = args.host_iface.split(',')
            if len(hif_split) < 2:
                print("When using dual interface mode, specify both SocketCan interfaces using commas: "
                      "--host-interface vcan0,vcan1!")
                parser.print_help()
                exit(-1)
            else:
                host_interface[0] = hif_split[0]
                host_interface[1] = hif_split[1]

        else:
            iface_num = int(iface_num)

    can_speed = 500000
    if (iface_num == 1 and not args.can1_speed) or (iface_num == 2 and not args.can2_speed):
        logging.warning(f"Using default can speed for CanBadger interface {iface_num}: {can_speed}")

    # print full configuration
    logging.info("# Configuration Summary")
    logging.info(f"Connecting to CanBadger: {cb_ip}")
    logging.info(f"Connecting to SocketCan Interface: {host_interface}")
    if dual_interface_mode:
        logging.info(f"Dual Interface Mode Active: {host_interface[0]} <-> CAN1, {host_interface[1]} <-> CAN2")
    if args.rx_only:
        logging.info("Disabling transmission (rx only mode)")
    logging.info("#")

    # start!
    processes = []
    queues = []
    #num_proc = 1 if not dual_interface_mode else 2
    num_proc = 1
    if dual_interface_mode:
        num_proc = 2
    for i in range(0,num_proc):
        #cb_to_sc_queue = Queue()
        #sc_to_cb_queue = Queue()
        queues.append(Queue())
        queues.append(Queue())
        processes.append(Process(target=process_canbadger, args=(cb_ip, 13371, host_ip, host_port, i+1,
                                                                 queues[(i*2)+0], queues[(i*2)+1])))
        processes.append(Process(target=process_socketcan, args=(host_interface[i], queues[(i*2)+1], queues[(i*2)+0])))

    for p in processes:
        p.start()

    for p in processes:
        p.join()


if __name__=='__main__':
    main()