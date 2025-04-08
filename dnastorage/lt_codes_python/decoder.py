from dnastorage.lt_codes_python.core import *
from reedsolo import RSCodec
from dnastorage.util.stats import *
import logging

logger = logging.getLogger()


def recover_graph(symbols, blocks_quantity, systematic, rs_size_fountain):
    """ Get back the same random indexes (or neighbors), thanks to the symbol id as seed.
    For an easy implementation purpose, we register the indexes as property of the Symbols objects.
    """

    for i, symbol in enumerate(symbols):
        stats.inc("fountain_drops", 1)
        #rs_obj = RSCodec(rs_size_fountain)
        checksum_len = 1
        checksum_pos = 0
        
        data = symbol.data[checksum_len:]
        
        if checksum(data) != symbol.data[checksum_pos]:
            logger.info(f"checksum failed for droplet checksumfromfile: {symbol.data[checksum_pos]} checksum: {checksum(data)} data: {symbol.data}")
            stats.inc("checksum_fountain_fail", 1)
            symbol.data = None
            continue

        else:
            logger.info(f"checksum passed for droplet")

        symbol.data = np.frombuffer(symbol.data, dtype=NUMPY_TYPE)

        symbol.data = symbol.data[checksum_len:]

        index = 0
        pos_degree = 0
        len_degree = 1
        pos_index = len_degree + pos_degree
        len_index = 4
        for i in range(len_index):
            index += int(symbol.data[i + pos_index]) * 256 ** i

        symbol.degree = int(symbol.data[pos_degree])
        symbol.index = index
        logger.info(f"generating indexes for index:{symbol.index}  degree: {symbol.degree} i = {i}")
        neighbors, deg = generate_indexes(symbol.index, symbol.degree, blocks_quantity, systematic)
        symbol.neighbors = {x for x in neighbors}
        symbol.data = symbol.data[len_degree + len_index:]

        if VERBOSE:
            symbol.log(blocks_quantity)

    return symbols

def reduce_neighbors(block_index, blocks, symbols):
    """ Loop over the remaining symbols to find for a common link between 
    each symbol and the last solved block `block`

    To avoid increasing complexity and another for loop, the neighbors are stored as dictionnary
    which enable to directly delete the entry after XORing back.
    """
    
    for other_symbol in symbols:
        if other_symbol.degree > 1 and other_symbol.data is not None and block_index in other_symbol.neighbors:
        
            # XOR the data and remove the index from the neighbors
            logger.info(f" index type: {type(blocks[block_index])} other data type: {type(other_symbol.data)}")
            logger.info(f"other_symbol data {other_symbol.data}")
            other_symbol.data = np.bitwise_xor(blocks[block_index], other_symbol.data)
            other_symbol.neighbors.remove(block_index)

            other_symbol.degree -= 1
            
            if VERBOSE:
                print("XOR block_{} with symbol_{} :".format(block_index, other_symbol.index), list(other_symbol.neighbors.keys())) 


def decode(symbols, blocks_quantity, systematic,packet_size, rs_size_fountain):
    """ Iterative decoding - Decodes all the passed symbols to build back the data as blocks. 
    The function returns the data at the end of the process.
    
    1. Search for an output symbol of degree one
        (a) If such an output symbol y exists move to step 2.
        (b) If no output symbols of degree one exist, iterative decoding exits and decoding fails.
    
    2. Output symbol y has degree one. Thus, denoting its only neighbour as v, the
        value of v is recovered by setting v = y.

    3. Update.

    4. If all k input symbols have been recovered, decoding is successful and iterative
        decoding ends. Otherwise, go to step 1.
    """

    symbols_n = len(symbols)
    assert symbols_n > 0, "There are no symbols to decode."

    # We keep `blocks_n` notation and create the empty list
    blocks_n = blocks_quantity
    blocks = [None] * blocks_n

    # Recover the degrees and associated neighbors using the seed (the index, cf. encoding).
    symbols = recover_graph(symbols, blocks_n, systematic, rs_size_fountain)
    print("Graph built back. Ready for decoding.", flush=True)
    
    solved_blocks_count = 0
    iteration_solved_count = 0
    start_time = time.time()
    
    while iteration_solved_count > 0 or solved_blocks_count == 0:
    
        iteration_solved_count = 0

        # Search for solvable symbols
        for i, symbol in enumerate(symbols):

            if symbol.data is None:
                logger.info(f"skipping droplet {i}")
                symbols.pop(i)
                continue

            # Check the current degree. If it's 1 then we can recover data
            if symbol.degree == 1: 

                iteration_solved_count += 1 
                block_index = next(iter(symbol.neighbors)) 
                symbols.pop(i)

                # This symbol is redundant: another already helped decoding the same block
                if blocks[block_index] is not None:
                    continue

                blocks[block_index] = symbol.data

                if VERBOSE:
                    print("Solved block_{} with symbol_{}".format(block_index, symbol.index))
              
                # Update the count and log the processing
                solved_blocks_count += 1
                log("Decoding", solved_blocks_count, blocks_n, start_time, packet_size)

                # Reduce the degrees of other symbols that contains the solved block as neighbor             
                reduce_neighbors(block_index, blocks, symbols)

    print("\n----- Solved Blocks {:2}/{:2} --".format(solved_blocks_count, blocks_n))

    
    for i in range(len(blocks)):
        if blocks[i] is None:
            blocks[i] = [0] * 32



    return np.asarray(blocks), solved_blocks_count
