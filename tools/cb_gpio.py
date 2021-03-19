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

    parser = argparse.ArgumentParser(description='CANBadger GPIO control')
    parser.add_argument('--ip', dest='ip', type=str, default=None,
                        help='CANBadger IP Address', required=True)
    parser.add_argument('--set', dest='set', type=int, default=None,
                        help="Set the state of the GPIO. Pass 1 or 0 (on or off). "
                             "If this isn't specified, we only read the state")
    parser.add_argument('--gpio-num', dest='num', type=int, default=1,
                        help='Which GPIO to operate on. Pass 1 or 2')
    parser.add_argument('--connect', dest='connect', default=False,
                        action='store_true', help='Connect to the CanBadger. This defaults to FALSE.'
                                                  'This means that if you are NOT running any other Tool '
                                                  'like the GUI or the SocketCan bridge, you need to pass this option,'
                                                  ' otherwise the CanBadger will reject our commands.'
                                                  'If you are running one of these tools in parallel,'
                                                  'then you do not need to pass this option.')


    args = parser.parse_args()

    if not args.ip:
        print("CANBadger IP or ID is required!")
        parser.print_help()
        exit(-1)


    if args.connect:
        # connect first
        print("Connecting not implemented yet!")
        exit(-1)

    if args.num not in [1,2]:
        print('Invalid Gpio Number! Pass 1 or 2.')
        parser.print_help()
        exit(-1)

    if args.ip:
        # try to parse it
        cb_ip = str(ipaddress.ip_address(args.ip))
    cb_aport = 13371

    if args.set not in [0, 1]:
        print("Invalid GPIO state! Pass 1 or 0 (for on or off)")
        parser.print_help()
        exit(-1)

    # send message
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    msg = None
    if args.set is None:
        msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.RELAY, 0, b'')
    else:
        # first byte is which gpio, second byte is desired state
        gpio = b'\x01'
        if args.num == 2:
            gpio = b'\x02'

        gpio_set = b'\x00'
        if args.set == 1:
            gpio_set = b'\x01'

    start_msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.RELAY, 2, gpio + gpio_set)
    sock.sendto(start_msg.serialize(), (cb_ip, cb_aport))


if __name__=='__main__':
    main()