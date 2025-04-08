#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import argparse
import numpy as np
import dnastorage.lt_codes_python.core as core
from dnastorage.lt_codes_python.decoder import decode
import random



def blocks_write(blocks, file, filesize, packet_size):
    """ Write the given blocks into a file
    """

    count = 0
    for data in blocks[:-1]:
        file.write(data)
        count += len(data)

    # Convert back the bytearray to bytes and shrink back 
    last_bytes = bytes(blocks[-1])
    shrinked_data = last_bytes[:filesize % packet_size]
    file.write(shrinked_data)

def decode_file(filename, outputname, file_blocks_n, file_size, systematic, packet_size, rs_size_fountain):

    # Generating symbols (or drops) from the blocks
    file_symbols = []
    with open(filename, 'rb') as output_f:
        print("ltdecode starting to read in fountain file")
        print(f"file size is {os.path.getsize(filename)}")
        data = output_f.read(packet_size + rs_size_fountain + 5)
        while len(data) != 0:
            print(len(data))
            if len(data) == packet_size + rs_size_fountain + 5:
                file_symbols.append(core.Symbol(index=0, degree=0, data=data))
            data = output_f.read(packet_size + rs_size_fountain + 5)

    
        
    #dump file_symbols into a file 'wb' write binary            

    # HERE: Simulating the loss of packets?

    # Recovering the blocks from symbols
    print("read back fountain file starting to decode")
    recovered_blocks, recovered_n = decode(file_symbols, file_blocks_n, systematic,packet_size, rs_size_fountain)
    
    if core.VERBOSE:
        print(recovered_blocks)
        print("------ Blocks :  \t-----------")
        # print(file_blocks)

    # if recovered_n != file_blocks_n:
    #     print("All blocks are not recovered, we cannot proceed the file writing")
    #     #fix me write recovered blocks to allow calculation of mismatched bytes
    #     return False

   

    # Write down the recovered blocks in a copy 
    with open(outputname, "wb") as file_copy:
        blocks_write(recovered_blocks, file_copy, file_size, packet_size)

    print("Wrote {} bytes in {}".format(os.path.getsize(outputname), outputname))
    return True




#########################################################
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Robust implementation of LT Codes encoding/decoding process.")
    parser.add_argument("filename", help="file path of the file to split in blocks")
    parser.add_argument("outputname", help="file path of the file to split in blocks")
    parser.add_argument("--systematic", help="ensure that the k first drops are exactaly the k first blocks (systematic LT Codes)", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("--x86", help="avoid using np.uint64 for x86-32bits systems", action="store_true")
    parser.add_argument("file_blocks_n", help = "file blocks size", type = int)
    parser.add_argument("file_size", help = "file size", type = int)
    args = parser.parse_args()

    core.NUMPY_TYPE = np.uint32 if args.x86 else core.NUMPY_TYPE
    core.SYSTEMATIC = True if args.systematic else core.SYSTEMATIC 
    core.VERBOSE = True if args.verbose else core.VERBOSE    

    print("Systematic: {}".format(core.SYSTEMATIC))

    filesize = os.path.getsize(args.filename)
    print("Filesize: {} bytes".format(filesize))

    # Splitting the file in blocks & compute drops

    decode_file(args.filename, args.outputname, args.file_blocks_n, args.file_size)
    
    print("Blocks: {}".format(args.file_blocks_n))

