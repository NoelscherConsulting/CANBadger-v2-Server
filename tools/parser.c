/*
* CanBadger Raw Log Parser
* Copyright (c) 2020 Noelscher Consulting GmbH
*
* Permission is hereby granted, free of charge, to any person obtaining a copy
* of this software and associated documentation files (the "Software"), to deal
* in the Software without restriction, including without limitation the rights
* to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
* copies of the Software, and to permit persons to whom the Software is
* furnished to do so, subject to the following conditions:
*
* The above copyright notice and this permission notice shall be included in
* all copies or substantial portions of the Software.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
* THE SOFTWARE.
*/

#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdint.h>
#include <stdbool.h>

const int HEADER_SIZE = 14;

uint32_t parseBigEndian32(unsigned char *source, size_t offset);
size_t goThroughLog(FILE *outptr, FILE *srcptr);
void displayHelp();
bool setFilename(char *namebuffer, char *nameorigin, size_t max_size);

int main(int argc, char *argv[]) {
    // prepare space for filenames
    char input_filename[201];
    char out_filename[201];
    bool in_set = false;
    bool out_set = false;

    // handle command line arguments
    uint8_t arg_it = 1;

    while(1) {
        if(arg_it==argc) {
            break;
        }
        int res = strncmp(argv[arg_it], "-", 1);
        if(res==0) {
            // have to parse a flag
            res = strcmp(argv[arg_it], "-f");
            if(res == 0) {
                // get input filename
                if(++arg_it == argc) {
                    printf("Missing filename after -f flag!");
                    return -1;
                }
                in_set = setFilename(input_filename, argv[arg_it], 200);
                if(!in_set) {
                    // error getting filename from args
                    printf(input_filename);
                    return -1;
                }
                arg_it++;
                continue;
            }
            res = strcmp(argv[arg_it], "-o");
            if(res == 0) {
                // get output filename
                if(++arg_it == argc) {
                    printf("Missing filename after -o flag!");
                    return -1;
                }
                out_set = setFilename(out_filename, argv[arg_it], 200);
                if(!out_set) {
                    // error getting filename from args
                    printf(out_filename);
                    return -1;
                }
                arg_it++;
                continue;
            }
            res = strcmp(argv[arg_it], "-h");
            if(res == 0) {
                displayHelp();
                return 0;
            }
            res = strcmp(argv[arg_it], "--help");
            if(res == 0) {
                displayHelp();
                return 0;
            }
            printf("error: unrecognised command line option '%s', use -h or --help to see valid options.", argv[arg_it]);
            return -1;
        } else {
            // no flag given, get in or output filename direktly
            if(!in_set) {
                in_set = setFilename(input_filename, argv[arg_it], 200);
                if(!in_set) {
                    // error getting filename from args
                    printf(input_filename);
                    return -1;
                }
            } else if(!out_set) {
                 out_set = setFilename(out_filename, argv[arg_it], 200);
                if(!out_set) {
                    // error getting filename from args
                    printf(out_filename);
                    return -1;
                }
            } else {
                // we dont care about the next args if filenames are set and its no flag
                break;
            }
        }
        arg_it++;
    }

    if(!in_set) {
        printf("Please specify the raw file to parse (-f filename)!");
        return -1;
    }
    if(!out_set) {
        strcpy(out_filename, "log.csv");
    }



    // open raw binary log
    FILE *srcptr = fopen(input_filename, "rb");
    if(srcptr == NULL) {
        printf("File %s was not found!", input_filename);
        return 1;
    }

    // create output log
    FILE *outptr = fopen(out_filename, "wt");
    if(outptr == NULL) {
        printf("Output %s could not be created!", out_filename);
        return 1;
    }

    // parse the raw log to readable log
    goThroughLog(outptr, srcptr);

    // close file streams
    if(srcptr != NULL) {
        fclose(srcptr);
    }
    if(outptr != NULL) {
        fclose(outptr);
    }

    return 0;
}

// converts the raw log from srcptr into readable .csv in outptr,
// returns count of parsed CAN frames
size_t goThroughLog(FILE *outptr, FILE *srcptr) {
    size_t cnt = 0;
    unsigned char header[HEADER_SIZE];
    uint8_t payload[256];
    size_t read;
    size_t written;

    while(1) {
        read = fread(header, HEADER_SIZE, 1, srcptr);  
        if(read != 1) {
            // EOF or invalid input
            break;
        }

        read = fread(payload, header[13], 1, srcptr);
        if(read != 1) {
            // invalid input
            break;
        }

        // get the timestamp
        uint32_t timestamp = parseBigEndian32(header, 1);
        fprintf(outptr, "%d, ", timestamp);

        // parse the interface byte
        switch(header[0]) {
            case 21:
                fprintf(outptr, "CAN1, Standard, ");
                break;
            case 22:
                fprintf(outptr, "CAN2, Standard, ");
                break;
            case 37:
                fprintf(outptr, "CAN1, Extended, ");
                break;
            case 28:
                fprintf(outptr, "CAN2, Extended, ");
                break;
            default:
                // invalid byte
                fprintf(outptr, "INV, INV, ");
        }

        // add speed, id and payload length
        uint32_t speed = parseBigEndian32(header, 9);
        fprintf(outptr, "%d, ", speed);
        uint32_t id = parseBigEndian32(header, 5);
        fprintf(outptr, "0x%x, %d", id, header[13]);

        // add payload
        for(uint8_t payload_it=0; payload_it<header[13]; payload_it++) {
            fprintf(outptr, ", 0x%x", payload[payload_it]);
        }
        fprintf(outptr, "\n");
    }

    return cnt;
}

// get a uint32_t from the 4 bytes in source at offset assuming they are BigEndian
uint32_t parseBigEndian32(unsigned char *source, size_t offset) {
    uint32_t value = source[offset];
    value = (value << 8) + source[offset+1];
    value = (value << 8) + source[offset+2];
    value = (value << 8) + source[offset+3];
    return value;
}

// copies the filename from nameorigin into the namebuffer if the string in nameorigin is
// smaller or equal to max_size and returns true
// returns false and printable error in namebuffer if the string is greater than max_size 
bool setFilename(char *namebuffer, char* nameorigin, size_t max_size) {
    if(strlen(nameorigin) <= max_size) {
        strcpy(namebuffer, nameorigin);
        return true;
    }
    sprintf(namebuffer, "Error: input filename (%d chars) longer than maximum of %d characters!",\
    strlen(nameorigin), max_size);
    return false;
}

// display command line help
void displayHelp() {
    printf("Usage: parser.exe [options] file...\n");
    printf("Options:\n");
    printf("%-12s%-12s\n", "--help", "Display this information.");
    printf("%-12s%-12s\n", "-h", "Display this information.");
    printf("%-12s%-12s\n", "-f", "Use to specify filename of raw log.");
    printf("%-12s%-12s\n", "-o", "Use to specify filename of parsed log.");
    printf("\nAlternative usage: parser.exe in_filename out_filename\n");
}