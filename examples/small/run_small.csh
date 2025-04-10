#!/bin/tcsh


python $DNASTORAGE_LSF/generate_fi_jobs.py --params $FRAMED_CONFIGS/small/base4_RS_ideal_cluster_iid_test.json --cores 8 --core_depth 1 --dump_dir $PWD  --queue short --time 1 --experiment_prefix framed_small_rs_fountain_testing_apr_10_7 --conda_env_path $FRAMED_CONDA --job_name "rs_cluster_fi"


# python $DNASTORAGE_LSF/generate_fi_jobs.py --params $FRAMED_CONFIGS/small/base4_RS_ideal_cluster_iid_sys.json --cores 128 --core_depth 1 --dump_dir $PWD  --queue short --time 1 --experiment_prefix framed_small_rs_fountain_test65_sys_and_nonsys --conda_env_path $FRAMED_CONDA --job_name "rs_cluster_fi"
# python $DNASTORAGE_LSF/generate_fi_jobs.py --params $FRAMED_CONFIGS/small/base4_RS_ideal_cluster_iid_nonsys.json --cores 128 --core_depth 1 --dump_dir $PWD  --queue standard --time 24 --experiment_prefix framed_small_rs_fountain_test11_nonsys --conda_env_path $FRAMED_CONDA --job_name "rs_cluster_fi"

# python $DNASTORAGE_LSF/generate_fi_jobs.py --params $FRAMED_CONFIGS/small/base4_RS_ideal_cluster_iid.json --cores 128 --core_depth 1 --dump_dir $PWD  --queue standard --time 24 --experiment_prefix framed_small_rs_nofountain_test7 --conda_env_path $FRAMED_CONDA --job_name "rs_cluster_fi"

# python $DNASTORAGE_LSF/generate_fi_jobs.py --params $FRAMED_CONFIGS/small/base4_RS_ideal_cluster_iid_test.json --cores 32 --core_depth 1 --dump_dir $PWD  --queue short --time 1 --experiment_prefix framed_small_rs_nofountain_testing13_moreparams --conda_env_path $FRAMED_CONDA --job_name "rs_cluster_fi"
# python $DNASTORAGE_LSF/generate_fi_jobs.py --params  $FRAMED_CONFIGS/small/basic_hedges_iid.json --cores 3 --core_depth 1 --dump_dir $PWD --experiment_prefix framed_small --conda_env_path $FRAMED_CONDA  --submission "shell"

# python $DNASTORAGE_LSF/generate_fi_jobs.py --params  $FRAMED_CONFIGS/small/basic_hedges_DNArSim.json --cores 3 --core_depth 1 --dump_dir $PWD --experiment_prefix framed_small --conda_env_path $FRAMED_CONDA  --submission "shell"

