"""
Main script for running fault injection analysis on different encoding architectures and fault environments.
"""
import mpi4py
from mpi4py import MPI
from dnastorage.fi.fi_env import *
from dnastorage.lt_codes_python.encode import encode_file
from dnastorage.lt_codes_python.decode import decode_file
import dnastorage.fi.dna_processes as dna_process
from dnastorage.system.pipeline_dnafile import *
from dnastorage.system.formats import *
from dnastorage.util.strandinterface import *
from dnastorage.util.mpi_logger import *
import dnastorage.util.generate as generate
import logging
import numpy as np
import sys
import os
import time
import copy
import json

logger = logging.getLogger()                                                                                                                                     

def get_param_files(args):
    if os.path.exists(args.enc_params):
        with open(args.enc_params,'rb') as param_file:
                encoding_params = json.load(param_file) #load in params for an encoding architecture through a json file
    if encoding_params is None:
        encoding_params={}
    if os.path.exists(args.header_params):
        with open(args.header_params,'rb') as param_file:
                header_params = json.load(param_file)#load in params for an encoding architecture through a json file
    if args.dna_process is not None and os.path.exists(args.dna_process):
        with open(args.dna_process,'rb') as param_file:
            strand_proc_dict = json.load(param_file)
    with open(args.fault_params,'rb') as param_file:
        fault_args = json.load(param_file)
    with open(args.distribution_params,'rb') as param_file:
        dist_args = json.load(param_file)
    with open(args.fi_env_params,'rb') as param_file:
        fi_env_args = json.load(param_file)
    assert fault_args !=None and dist_args !=None and fi_env_args!=None
    return encoding_params,header_params,strand_proc_dict,fault_args,dist_args,fi_env_args


def is_master(comm):
    return comm==None or comm.Get_rank()==0 #check if this is a master process


def _monte_kernel(monte_start,monte_end,args,comm=None): #function that will run per process  
    #We cant use the data_keeper object here, should be private per process, need data structures to propagate results back up to parent process
    results=[] #each element will be an object that encapsulates the entire statistics
    stats.clear()
    strand_interface = BaseStrandInterface.open("array")
    encoding_params,header_params,strand_proc_dict,fault_args,dist_args,fi_env_args = get_param_files(args)
    header_data_path = os.path.join(args.out_dir,"header_pipeline{}.header".format(monte_end)) #binary data output for header of the header's pipeline
    payload_header_data_path = os.path.join(args.out_dir,"payload_pipeline{}.header".format(monte_end)) #binary data output for header of the payload pipeline
    #non-master ranks don't really need to encode
    if is_master(comm):
        
        fountainless_file_size = os.path.getsize(args.file)
        fountain_encode_basename = f"{os.path.basename(args.file)}{monte_end}.bin"

        systematic_true = False
        if encoding_params["systematic"] == 1:
            systematic_true = True
        if encoding_params["fountain_redundancy"] != 1:
            file_blocks_n = encode_file(args.file, fountain_encode_basename, encoding_params["fountain_redundancy"], systematic_true, encoding_params["packet_size"], encoding_params["rs_size_fountain"])
            file_to_fault_inject= open(fountain_encode_basename, "rb")
            logger.info("fountain encoding finished")
        else:
            file_to_fault_inject= open(args.file, "rb")
        
        file_to_fault_inject.seek(0,2)
        file_to_inject_size=file_to_fault_inject.tell()
        file_to_fault_inject.seek(0,0)
        #we give the .dna to each instance, whether we actually write it, to make sure header data is consistent across runs
        base_file_path  = os.path.basename(args.file)
        if monte_end!=args.num_sims: 
            write_dna = DNAFilePipeline.open("w",format_name=args.arch,header_params=header_params,header_version=args.header_version,
                                             
                                             encoder_params=encoding_params,fsmd_header_filename=header_data_path, payload_header_filename = payload_header_data_path,
                                             file_barcode=tuple(args.file_barcode),do_write=False,dna_file_name="{}.dna".format(base_file_path),store_header=args.store_header)
        else: #save 1 copy of the DNA file
            write_dna = DNAFilePipeline.open("w",format_name=args.arch,header_params=header_params,header_version=args.header_version,
                                             encoder_params=encoding_params,fsmd_header_filename=header_data_path,file_barcode=tuple(args.file_barcode),
                                             payload_header_filename = payload_header_data_path,do_write=True,dna_file_name=os.path.join(args.out_dir,"{}.dna".format(base_file_path)),
                                             store_header=args.store_header)

        write_dna.write(file_to_fault_inject.read())
        write_dna.close()
        stats["total_encoded_strands"]=len(write_dna.strands)
        stats["header_strand_length"]=len(write_dna.strands[0].dna_strand) #header strands should be first
        stats["payload_strand_length"]=len(write_dna.strands[-1].dna_strand)#strands with real payload should be at the end
        stats["dead_header"]=0
        stats["file_size_bytes"]=file_to_inject_size

        #do some basic processes on the DNA strands
        if strand_proc_dict is not None:
            #do some strand processing
            for s in write_dna.strands:
                for process in strand_proc_dict:
                    func = getattr(dna_process,process)
                    s.dna_strand = func(s.dna_strand,*strand_proc_dict[process])

    #Encode file we are fault injecting on
    if is_master(comm): fault_environment =  Fi_Env(write_dna.strands,dist_args,fault_args,**fi_env_args)
    stats.experiment_counter=monte_start
    for sim_number in range(monte_start,monte_end):
        logger.info("Monte Carlo Sim: {}".format(sim_number))
        strands=None
        if is_master(comm):
            fault_environment.Run()
            strands = fault_environment.get_strands()
            strand_interface.strands=strands

        read_dna = DNAFilePipeline.open("r",header_params=header_params,
                                        header_version=args.header_version,format_name=args.arch,encoder_params=encoding_params,
                                        fsmd_header_filename=header_data_path,file_barcode=tuple(args.file_barcode),
                                        payload_header_filename = payload_header_data_path,mpi=comm,strand_interface=strand_interface,
                                        store_header=args.store_header)

        if not is_master(comm): continue
        
        stats.inc("total_file_data_bytes",stats["file_size_bytes"])
        stats.inc("total_strands_analyzed",len(fault_environment.get_strands()))
        #calculate missing bytes
        file_to_fault_inject.seek(0,0)
        total_mismatch_data=0
        length_fi_data=0
        index=0
        while True:
            fi_data=read_dna.read(1)
            if len(fi_data)==0: break
            original_data=file_to_fault_inject.read(1)
            if len(original_data)==0: break
            length_fi_data+=1
            index+=1
            if fi_data==original_data:
                continue
            else:
                total_mismatch_data+=1
        stats.inc("total_mismatch_bytes",total_mismatch_data)
        stats.inc("file_size_difference_bytes",abs(file_to_inject_size-length_fi_data))
        if total_mismatch_data>0 or file_to_inject_size!=length_fi_data:
            stats.inc("error",1)
        else:
            stats.inc("error",0)
        logger.info("Finished decoding erroneous file")

        if encoding_params["fountain_redundancy"] != 1:

            fountainless_file = open(args.file, "rb")
            fountainless_file.seek(0,0)
            total_mismatch_data=0
            length_fi_data=0
            index=0
            fountain_to_decode_filename = f"{fountain_encode_basename}.{sim_number}.bin"
            with open(fountain_to_decode_filename, "wb") as decoded_fountain_file: 
                logger.info("starting to put fountain file in")
                read_dna.reset()
                while True:
                    x = read_dna.read(1)
                    if len(x) == 0:
                        break
                    decoded_fountain_file.write(x)
                logger.info("finished writing fountain file in")

            decoded_fountain_filename = f"{fountain_encode_basename}.{sim_number}.decoded.bin"

            bol = decode_file(fountain_to_decode_filename, decoded_fountain_filename, file_blocks_n, fountainless_file_size, systematic_true, encoding_params["packet_size"], encoding_params["rs_size_fountain"])
        
            logger.info("finished decoding")
            decodedFountain = open(decoded_fountain_filename, "rb")
            decodedFountain.seek(0,0)
            fountain_total_mismatch_data=0
            fountain_length_fi_data=0
            index=0
            while True: #make comparision a function to use for before and after fountain
                #check this while loop
                fi_data=decodedFountain.read(1)
                if len(fi_data)==0: break
                original_data=fountainless_file.read(1)
                if len(original_data)==0: break
                fountain_length_fi_data+=1
                index+=1
                if fi_data==original_data:
                    continue
                else:
                    fountain_total_mismatch_data+=1
            stats.inc("total_mismatch_bytes_after_fountain",fountain_total_mismatch_data)
            stats.inc("file_size_difference_bytes_after_fountain",abs(fountainless_file_size-fountain_length_fi_data))
            if fountain_total_mismatch_data>0 or fountainless_file_size!=fountain_length_fi_data:
                stats.inc("error_after_fountain",1)
            else:
                stats.inc("error_after_fountain",0)
            logger.info("Finished decoding erroneous fountain file")
        else:
            logger.info("failed_fountain_decoding")
            stats.inc("fountain_fail", 1)
        

    #merge in results from different ranks
    if comm:
        all_stats = comm.gather(stats,root=0)
        if not is_master(comm): return None #dont care what helper returns
        stats.clear() #make sure to merge into clean stats
        for s in all_stats:
            stats.aggregate(s)

    results.append(copy.deepcopy(stats)) #Todo: could probably get rid of this 
    if monte_end!=args.num_sims: #save last header data incase we want to keep it
        os.remove(header_data_path)
        os.remove(payload_header_data_path)
    file_to_fault_inject.close()    
    return results


def _monte_parallel_wrapper(task,task_comm=None): #wrapper for parallelization
    monte_start,monte_end,args = task
    logger.info("Rank {} Beginning to run monte task".format(MPI.COMM_WORLD.rank))
    logger.info("Monte Carlo Sim: Start {} END {}".format(monte_start,monte_end))
    return _monte_kernel(monte_start,monte_end,args,comm=task_comm)

#function for running monte carlo simulations for a fixed rate fault model
def run_monte(pool,args):
    logger.info("Rank {} Building Tasks".format(MPI.COMM_WORLD.rank)) 
    #run many simulations to perform statistical analysis
    stats_file_path =os.path.join(args.out_dir,"fi.stats")
    stats_pickle_path = os.path.join(args.out_dir,"fi.pickle")
    stats_fd = open(stats_file_path,'w+')
    pickle_fd=open(stats_pickle_path,'wb+')
    dist=[]
    monteIters=args.num_sims//args.cores
    last_monte_iter = args.num_sims%args.cores
    processIters=0
    tasks=[] #list of arguments for each task
    for i in range(args.cores):
        if i==args.cores-1:
            tasks.append((processIters,processIters+monteIters+last_monte_iter,args))
        else:
            tasks.append((processIters,processIters+monteIters,args))
        processIters+=monteIters #set up next range of montecarlo simulations

    results = pool.map(_monte_parallel_wrapper,tasks) #map the work to different processes

    pool.close() #close the pool
    
    total_results=[]
    for job_res in results:#unpack results from jobs
        for res in job_res:
            total_results.append(res)
    stats.clear()
    stats.set_fd(stats_fd)
    stats.set_pickle_fd(pickle_fd)
    #need to aggregate data across all results
    for s in total_results:
        stats.aggregate(s,["total_encoded_strands","header_strand_length","payload_strand_length",
                           "file_size_bytes","index_dist_encode"]) #just want to copy information about total strands/strand_length
    stats["total_runs"]=args.num_sims
    stats.persist()
    stats_fd.close()
    pickle_fd.close()

if __name__ == "__main__":
    import argparse
    import schwimmbad
    
    comm=MPI.COMM_WORLD
    
    parser = argparse.ArgumentParser(description="Inject faults into input file and perform analysis")
    parser.add_argument('--simulation_runs',dest="num_sims",action="store",type=int,default=1000,help="Number of simulations to run")
    parser.add_argument('--arch',required=True,choices=file_system_formats(),help="Encoding/decoding architecture")
    parser.add_argument('--file',required=True,help = "File to fault inject on")
    parser.add_argument('--cores', type=int, action="store",default=1,help="Number of threads to run monte carlo simulations")
    parser.add_argument('--enc_params',type=str,required=True,action="store",help="Path to json file with parameters used to set error correction in encoding")
    parser.add_argument('--header_params',type=str,required=True,action="store",help="Path to json file with parameters used to set error correction in encoding for the header")
    parser.add_argument('--header_version',type=str,required=False,action="store",default="0.1",help="Header version")
    parser.add_argument('--distribution_params',required=True,action="store",help="Parameters used to specify the distribution")
    parser.add_argument('--fault_params',required=True,action="store",help="Parameters used to specify the fault model")
    parser.add_argument('--fi_env_params',required=True,action="store",help="Parameters for the fault injection environment")
    parser.add_argument('--dna_process',required=False,default=None,help="set of processing steps to do on dna strands before fault injection")
    parser.add_argument('--out_dir',type=str,required=True,action="store",help="Directory where data will be dumped")
    parser.add_argument('--file_barcode',required=False,default=tuple(),nargs="+",type=int,help="Barcode for the file")
    parser.add_argument('--store_header',required=False,default=1,type=int,help="Whether to store header data")

    args = parser.parse_args()
    if args.store_header==1: args.store_header=True
    else: args.store_header=False
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')                                                                                           
    mpi_handler = MPIFileHandler(os.path.join(args.out_dir,"fi_info_{}.log".format(comm.rank)))
    mpi_handler.setFormatter(formatter)                                                                                                                                             
    logger.addHandler(mpi_handler)                                                                                                                                                  
    logger.setLevel(logging.INFO)
    assert os.path.isdir(args.out_dir)                                                                                                                                             

    #TODO: Have some support for recreating results from a set of seeds. For now, just spit out the seeds
    #set seeds for each process, this just ensures that not everyone is initialized off the same seed
    seed = generate.seed()
    generate.set_seed(seed)

    if comm.Get_rank()>args.cores:
        seed=0 #0 out seed of helper cores
        
    logger.info("SEED {} for RANK {}".format(seed,comm.rank))
    logger.info("Processor name {}".format(MPI.Get_processor_name()))
    logger.info("PID of Rank {}".format(os.getpid()))
    #gather all seeds for the main process to print
    seeds = comm.gather(seed,root=0)
    if comm.rank ==0:
        logger.info("Printing Gathered Seeds")
        for i in seeds:
            logger.info("SEED: {}".format(i))

    #create pool of workers, only rank 0 should continue from here
    pool = schwimmbad.choose_pool(mpi=True,processes=args.cores,comm=MPI.COMM_WORLD)
    run_monte(pool,args)
