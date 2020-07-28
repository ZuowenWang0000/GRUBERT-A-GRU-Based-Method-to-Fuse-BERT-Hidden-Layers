# Table of Contents
- [Preparations](#preparations)
  * [Dependencies](#dependencies)
  * [Dataset](#dataset)
- [Training](#training)
  * [Available models and embeddings](#available-models-and-embeddings)
    + [Compatible Flair-based embeddings](#compatible-flair-based-embeddings)
      - [Additional embedding files required for GloVe and SynGCN](#additional-embedding-files-required-for-glove-and-syngcn)
    + [Compatible transformers-based embeddings](#compatible-transformers-based-embeddings)
- [Prediction](#prediction)
- [Configuration Files](#configuration-files)

# Preparations

## Dependencies 
For Leonhard users, to install dependencies, please first execute
```
module load eth_proxy
module load gcc/6.3.0 python_gpu/3.7.4 hdf5
```
Then one can use pip to install
```
pip3 install --user requirment.txt
```
to install the dependencies needed. Virtual environment is recommended.

## Dataset
Download the tweet datasets from [here](https://polybox.ethz.ch/index.php/s/Tb0QWEKEK9Bhiqy?path=%2Fdataset%2Ffinal_dataset).

This link contains a train split, a validation split and a test split (label unknown). The train and validation splits are created by spliting the original training set provided by the ETH CIL course team.
These datasets are preprocessed using the same preprocessing procedure described in the report (section?).

# Training
For Leonhard users please execute train.sh with flags:
```
./train.sh --config configs/the_experiment_config_file.json --embedding <embedding>
```

For non-Leonhard users please execute the python train.py script. Flags are the same as on Leonhard and can be viewed using `python train.py --help`


an example for a quick start on Leonhard:
```
./train.sh --config configs/bert_mix.json --embedding bert_mix --seed 0
```

## Available models and embeddings
There are two classes of models: models that operate on bert-based embeddings from huggingface's transformers library, and models that operate on embeddings provided by the Flair NLP library. In general, flair-based models (GSFlairMixModel, LstmModel) can operate with any compatible flair-based embedding (see list below), and bert-based models (BertMixModel, BertWSModel, BertLinearModel, BertMixLSTMModel) can operate on any compatible transformers-based embedding (see list below)

### Compatible Flair-based embeddings
GloVe and SynGCN embeddings require additional files to be present in the `./embeddings` directory (see the next section)

- `flair`: Uses a mix of GloVe, SynGCN, and Flair forward and backward embeddings 
- `elmo`: Uses a mix of GloVe, SynGCN, and ELMo embeddings
- `bert`: Uses a mix of GloVe, SynGCN, and BERT embeddings
- `glove-only`: Uses GloVe embeddings
- `syngcn-only`: Uses SynGCN embeddings
- `glove-syngcn`: Uses a mix of GloVe and SynGCN embeddings
- `twitter-only`: Uses Twitter embeddings from Flair

#### Additional embedding files required for GloVe and SynGCN

These are available for download [here](https://polybox.ethz.ch/index.php/s/Tb0QWEKEK9Bhiqy?path=%2Fembeddings) and should be placed into the `./embeddings` directory.

### Compatible transformers-based embeddings
- `bert-mix`: Uses BERT embeddings, exposing all 12 hidden layers
- `roberta-mix`: Uses Roberta embeddings, exposing all 12 hidden layers

# Prediction
We save a checkpoint every epoch. For making prediction on the test dataset, one needs to run the 
predict.sh script and specify the config file, checkpoint path and the file name where the predictions are stored. An example is as follows:
```
./predict.sh --config config/the_experiment_config_file.json --checkpoint_path /cluster/scratch/hoffmannthebestman/log_dir/bert_mix_seed0/checkpoint_han_2.tar --predict-file ./pred_bert_mix_s0.csv
```

# Configuration Files
A typical configuration file to control the model type, model parameter and experiment environment looks as follows:
```
{
    "model": {  # NOTE: model parameters differ according to the model; this is an example for a BertMixModel config
        "architecture": "BertMixModel",   # other options: see previous section
        "n_classes": 2,  # number of classes for prediction (here, just positive and negative)
        "gru_hidden_size": 100,  # the number of hidden units in each GRU used in the model, plz refer to section XX in the paper
        "num_gru_layers": 1, # the number of layer in each GRU used in the model.
        "num_grus": 3, # the number of GRUs used to fuse the bert layers
        "linear_hidden_size": 100, # the number of hidden units for the linear classifier layer 
        "dropout": 0.5, 
        "fine_tune_embeddings": true, # to reveal the true power of bert, fine-tune need to be enabled
        "sentence_length_cut": 40, 
        "use_regularization": "none",  # parameters used in the experiment in appendix XX
        "regularization_lambda": 0  # for appendix XX
    },
    "training": {
        "start_epoch": 0,  # the starting epoch, only used for continue training, otw set to 0
        "batch_size": 64,  
        "lr": 1e-5,
        "lr_decay": 0.9, # after each iteration, the learning rate will be set to previous learning rate * lr_decay
        "momentum": 0.9,
        "workers": 0, 
        "epochs": 30,
        "grad_clip": "none",
        "print_freq": 250,
        "checkpoint": "none",
        "save_checkpoint_freq_epoch": 1,  
        "save_checkpoint_path": "/cluster/scratch/__USER__/log_dir/mix_bert_bs64",  # specify the path to save the checkpoint 
            # -- NOTE: if training on a local machine instead of Leonhard, the checkpoint path will need to be changed
        "train_without_val": false,
        "weight_decay":0.0
    },
    "dataset": {
        "dataset_dir": "../dataset",  # the dataset folder (which includes train, validation and test files)
        "rel_train_path": "train_split.csv",
        "rel_val_path": "val_split.csv",
        "rel_test_path": "test_cleaned.csv"
    }
}

```




