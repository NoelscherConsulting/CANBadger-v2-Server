#####################################################################################
# CanBadger UDS Enums                                                               #
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

from enum import IntEnum


class UdsDiagnosticSessionType(IntEnum):
    DEFAULT = 0x01
    PROGRAMMING = 0x02
    EXTENDED = 0x03
    SAFETY_SYSTEM = 0x04
    # 40-5f is oem specific
    # 60 - 7e is system supplier specific


class UdsServiceIdentifier(IntEnum):
    DIAGNOSTIC_SESSION_CONTROL=0x10
    ECU_RESET=0x11
    CLEAR_DIAGNOSTIC_INFORMATION=0x14
    SECURITY_ACCESS=0x27
    COMMUNICATION_CONTROL=0x28
    ACCESS_TIMING_PARAMETERS=0x83
    SECURED_DATA_TRANSMISSION=0x84
    CONTROL_DTC_SETTINGS=0x85
    RESPONSE_ON_EVENT=0x86
    LINK_CONTROL=0x87
    READ_DATA_BY_ID=0x22
    READ_MEMORY_BY_ADDRESS=0x23
    READ_SCALING_DATA_BY_ID=0x24
    READ_DATA_BY_PERIODIC_ID=0x2A
    DYNAMICALLY_DEFINE_DATA_ID=0x2C
    WRITE_DATA_BY_ID=0x2E
    WRITE_MEMORY_BY_ADDRESS=0x3D
    READ_DTC_INFORMATION=0x19
    INPUT_OUTPUT_CONTROL_BY_ID=0x2F
    ROUTINE_CONTROL=0x31
    REQUEST_DOWNLOAD=0x34
    REQUEST_UPLOAD=0x35
    TRANSFER_DATA=0x36
    REQUEST_TRANSFER_EXIT=0x37
    REQUEST_FILE_TRANSFER=0x38
    TESTER_PRESENT=0x3E


class UdsNegativeResponse(IntEnum):
    NEGATIVE_RESPONSE=0x7F
    GENERAL_REJECT=0x10
    SERVICE_NOT_SUPPORTED=0x11
    SUBFUNCTION_NOT_SUPPORTED=0x12
    INCORRECT_MESSAGE_LENGTH_OR_INVALIDAD_FORMAT=0x13
    RESPONSE_TOO_LONG=0x14
    BUSY_REPEAT_REQUEST=0x21
    CONDITIONS_NOT_CORRECT=0x22
    ROUTINE_NOT_COMPLETE=0x23
    REQUEST_SEQUENCE_ERROR=0x24
    NO_RESPONSE_FROM_SUBNET_COMPONENT=0x25
    FAILURE_PREVENTS_EXECUTION_OF_REQUESTED_ACTION=0x26
    REQUEST_OUT_OF_RANGE=0x31
    SECURITY_ACCESS_DENIED=0x33
    INVALID_KEY=0x35
    EXCEEDED_NUMBER_OF_ATTEMPTS=0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED=0x37
    DOWNLOAD_NOT_ACCEPTED=0x40
    IMPROPER_DOWNLOAD_TIME=0x41
    CANT_DOWNLOAD_TO_SPECIFIED_ADDRESS=0x42
    CANT_DOWNLOAD_NUMBER_OF_BYTES_REQUESTED=0x43
    UPLOAD_NOT_ACCEPTED=0x50
    IMPROPER_UPLOAD_TYPE=0x51
    CANT_UPLOAD_FROM_SPECIFIED_ADDRESS=0x52
    CANT_UPLOAD_NUMBER_OF_BYTES_REQUESTED=0x53
    """ RANGE
    0x38 - 0x4F
    RESERVED
    BY
    ISO
    15764
    """
    UPLOAD_DOWNLOAD_NOT_ACCEPTED=0x70
    TRANSFER_DATA_SUSPENDED=0x71
    GENERAL_PROGRAMMING_FAILURE=0x72
    WRONG_BLOCK_SEQUENCE_COUNTER=0x73
    ILLEGAL_ADDRESS_IN_BLOCK_TRANSFER=0x74
    ILLEGAL_BYTE_COUNT_IN_BLOCK_TRANSFER=0x75
    ILLEGAL_BLOCK_TRANSFER_TYPE=0x76
    BLOCK_TRANSFER_DATA_CHECKSUM_ERROR=0x77
    RESPONSE_PENDING=0x78
    INCORRECT_BYTE_COUNT_DURING_BLOCK_TRANSFER=0x79
    SUBFUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION=0x7E
    SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION=0x7F
    SERVICE_NOT_SUPPORTED_IN_ACTIVE_DIAGNOSTIC_MODE=0x80
    RPM_TOO_HIGH=0x81
    RPM_TOO_LOW=0x82
    ENGINE_IS_RUNNING=0x83
    ENGINE_IS_NOT_RUNNING=0x84
    ENGINE_RUN_TIME_TOO_LOW=0x85
    TEMPERATURE_TOO_HIGH=0x86
    TEMPERATURE_TOO_LOW=0x87
    VEHICLE_SPEED_TOO_HIGH=0x88
    VEHICLE_SPEED_TOO_LOW=0x89
    THROTTLE_TOO_HIGH=0x8A
    THROTTLE_TOO_LOW=0x8B
    TRANSMISSION_RANGE_NOT_IN_NEUTRAL=0x8C
    TRANSMISSION_RANGE_NOT_IN_GEAR=0x8D
    BRAKE_SWITCH_NOT_CLOSED=0x8F
    SHIFTER_LEVER_NOT_IN_PARK=0x90
    TORQUE_CONVERTER_CLUTCH_LOCKED=0x91
    VOLTAGE_TOO_HIGH=0x92
    VOLTAGE_TOO_LOW=0x93