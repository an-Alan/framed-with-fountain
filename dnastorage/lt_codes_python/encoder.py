from dnastorage.lt_codes_python.core import *
from dnastorage.lt_codes_python.distributions import *
from dnastorage.codec.strand import *
from reedsolo import RSCodec
import logging

logger = logging.getLogger()

def get_degrees_from(distribution_name, N, k):
    """ Returns the random degrees from a given distribution of probabilities.
    The degrees distribution must look like a Poisson distribution and the 
    degree of the first drop is 1 to ensure the start of decoding.
    """

    if distribution_name == "ideal":
        probabilities = ideal_distribution(N)
    elif distribution_name == "robust":
        probabilities = robust_distribution(N)
    else:
        probabilities = None
    
    population = list(range(0, N+1))
    degrees = choices(population, probabilities, k=k-1)
    assert 0 not in degrees, "0 in degrees"
    return [1] + degrees

   
def encode(blocks, drops_quantity, systematic, packet_size, rs_size_fountain):
    """ Iterative encoding - Encodes new symbols and yield them.
    Encoding one symbol is described as follow:

    1.  Randomly choose a degree according to the degree distribution, save it into "deg"
        Note: below we prefer to randomly choose all the degrees at once for our symbols.

    2.  Choose uniformly at random 'deg' distinct input blocs. 
        These blocs are also called "neighbors" in graph theory.
    
    3.  Compute the output symbol as the combination of the neighbors.
        In other means, we XOR the chosen blocs to produce the symbol.
    """

    # Display statistics
    blocks_n = len(blocks)
    assert blocks_n <= drops_quantity, "Because of the unicity in the random neighbors, it is need to drop at least the same amount of blocks"

    print("Generating graph...")
    start_time = time.time()

    # Generate random indexes associated to random degrees, seeded with the symbol id
    random_degrees = get_degrees_from("robust", blocks_n, k=drops_quantity)

    print("Ready for encoding.", flush=True)

    for i in range(drops_quantity):
        
        # Get the random selection, generated precedently (for performance)
        selection_indexes, deg = generate_indexes(i, random_degrees[i], blocks_n, systematic)

        # Xor each selected array within each other gives the drop (or just take one block if there is only one selected)
        drop = blocks[selection_indexes[0]]
        for n in range(1, deg):
            drop = np.bitwise_xor(drop, blocks[selection_indexes[n]])
            # drop = drop ^ blocks[selection_indexes[n]] # according to my tests, this has the same performance
            # print(drop)
        # Create symbol, then log the process
        index = [0, 0, 0, 0]
        indexbefore = i
        counter = 0
        while i > 0:
            index[counter] = i%256
            i = i // 256
            counter += 1
            assert counter < 4

        drop = np.insert(drop, 0, index)
        assert deg <= 255 and deg > 0, f"degree: {deg}"
        drop = np.insert(drop, 0, deg)

        #rs_obj = RSCodec(rs_size_fountain)
        #drop = np.frombuffer(rs_obj.encode(drop), dtype=NUMPY_TYPE)
        # checksumd = checksum(drop)
        # drop = np.insert(drop, 0, checksumd)
        crc = CRC8()
        logger.info(f"droplet {indexbefore} checksum = {crc._crc(drop)}")
        drop = np.frombuffer(np.insert(drop, 0 ,crc._crc(drop)), dtype=NUMPY_TYPE)
        symbol = Symbol(index=i, degree=deg, data=drop)
        
        if VERBOSE:
            symbol.log(blocks_n)

        log("Encoding", i, drops_quantity, start_time, packet_size)

        yield symbol

    print("\n----- Correctly dropped {} symbols (packet size={})".format(drops_quantity, packet_size))
