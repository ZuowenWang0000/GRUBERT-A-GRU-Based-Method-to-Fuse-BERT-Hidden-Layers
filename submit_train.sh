#!/bin/sh

bsub -J $JOB_NAME -n 1 -W $ttime -R "rusage[mem=$mem_per_gpu, ngpus_excl_p=$num_gpu_per_job]" -R "select[gpu_model1==$gpu_type]" \
TF_XLA_FLAGS=--tf_xla_cpu_global_jit python3 train.py $@
