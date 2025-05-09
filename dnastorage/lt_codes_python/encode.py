#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import argparse
import numpy as np
import dnastorage.lt_codes_python.core as core
from dnastorage.lt_codes_python.encoder import encode
import random
import logging

logger = logging.getLogger()

def blocks_read(file, filesize, packet_size):
    """ Read the given file by blocks of `core.PACKET_SIZE` and use np.frombuffer() improvement.

    Byt default, we store each octet into a np.uint8 array space, but it is also possible
    to store up to 8 octets together in a np.uint64 array space.  
    
    This process is not saving memory but it helps reduce dimensionnality, especially for the 
    XOR operation in the encoding. Example:
    * np.frombuffer(b'\x01\x02', dtype=np.uint8) => array([1, 2], dtype=uint8)
    * np.frombuffer(b'\x01\x02', dtype=np.uint16) => array([513], dtype=uint16)
    """

    blocks_n = math.ceil(filesize / packet_size)
    blocks = []

    # Read data by blocks of size core.PACKET_SIZE
    for i in range(blocks_n):
            
        data = bytearray(file.read(packet_size))

        if not data:
            raise "stop"

        # The last read bytes needs a right padding to be XORed in the future
        if len(data) != packet_size:
            data = data + bytearray(packet_size - len(data))
            assert i == blocks_n-1, "Packet #{} has a not handled size of {} bytes".format(i, len(blocks[i]))

        # Paquets are condensed in the right array type
        blocks.append(np.frombuffer(data, dtype=core.NUMPY_TYPE))

    return blocks

def encode_file(filename,outputname, redundancy, systematic, packet_size, rs_size_fountain):

    with open(filename, "rb") as file:

        logger.info("Redundancy: {}".format(redundancy))
        logger.info("Systematic: {}".format(systematic))

        filesize = os.path.getsize(filename)
        assert filesize > 0
        logger.info("Filesize: {} bytes".format(filesize))

        # Splitting the file in blocks & compute drops
        file_blocks = blocks_read(file, filesize, packet_size)
        file_blocks_n = len(file_blocks)
        drops_quantity = int(file_blocks_n * redundancy)

        logger.info("Blocks: {}".format(file_blocks_n))
        logger.info("Drops: {}\n".format(drops_quantity))

        # Generating symbols (or drops) from the blocks
        file_symbols = []
        with open(outputname, 'wb') as output_f:
            for curr_symbol in encode(file_blocks, drops_quantity, systematic,packet_size, rs_size_fountain):
            # if random.random() < 0.1:
            #     curr_symbol.data[9] = ~curr_symbol.data[9]
                
            #     logger.info("changed bytes")
                # file_symbols.append(curr_symbol)
                for char in curr_symbol.data:
                    output_f.write(char)
            
    logger.info(f"file_blocks_n = {file_blocks_n}")
    logger.info(f"finished encoding, dumped data into {outputname}")
    return(file_blocks_n)
    


#########################################################
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Robust implementation of LT Codes encoding/decoding process.")
    parser.add_argument("filename", help="file path of the file to split in blocks")
    parser.add_argument("outputname", help="file path of the file to split in blocks")
    parser.add_argument("-r", "--redundancy", help="the wanted redundancy.", default=2.0, type=float)
    parser.add_argument("--systematic", help="ensure that the k first drops are exactaly the k first blocks (systematic LT Codes)", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("--x86", help="avoid using np.uint64 for x86-32bits systems", action="store_true")
    args = parser.parse_args()

    core.NUMPY_TYPE = np.uint32 if args.x86 else core.NUMPY_TYPE
    core.SYSTEMATIC = True if args.systematic else core.SYSTEMATIC 
    core.VERBOSE = True if args.verbose else core.VERBOSE    

    encode_file(args.filename, args.outputname, args.redundancy)

