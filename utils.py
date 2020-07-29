import torch
from torch.utils.data import DataLoader, TensorDataset
import numpy as np


def load_train(train_on_full = False):
    '''
    :parameter
    train_full:bool
        if true, load the full dataset

    :returns
    train_pos: a list of strings containing all positive texts
    train_neg: a list of strings containing all negative texts
    vocab: a list of strings containing all vocabulary

    '''
    if(train_on_full == False):
        train_file_pos_path = "./dataset/train_pos.txt"
        train_file_neg_path = "./dataset/train_neg.txt"
        vocab_file_path = "./dataset/vocab_cut.txt"
    else:
        train_file_pos_path = "./dataset/train_pos_full.txt"
        train_file_neg_path = "./dataset/train_neg_full.txt"
        vocab_file_path = "./dataset/vocab_cut.txt"

    with open(vocab_file_path, 'r') as f_vocab:
        vocab = f_vocab.read().split()
    with open(train_file_pos_path, 'r') as f_pos:
        pos_text = f_pos.read().splitlines()
    with open(train_file_neg_path, 'r') as f_neg:
        neg_text = f_neg.read().splitlines()

    return pos_text, neg_text, vocab

def make_labels(size_pos, size_neg):
    '''
    :parameter
    size_pos: int
        number of tweets of positive sentiment
    size_neg: int
        number of tweets of negative sentiment

    :returns
    a list of labels +1, -1 of [size_pos times of 1, size_neg times of -1]

    '''

    return [1 for i in range(size_pos)] + [-1 for i in range(size_neg)]

def load_embedding(vocab, embedding_path):
    """
    :parameter
    vocab: list
        a list of strings containing all vocabularies
    embedding_path: string
        the path to the embedding, i.e. std_glove_embeddings
    :return
    embeddings_dict: dict
        a dictionary contains mapping from words to vectors
    """
    embeddings_dict = {}
    with np.load(embedding_path, 'r') as f:
        """
            f['arr_0'] is word embedding, f['arr_1'] is context embedding
        """
        embeddings_dict = dict(zip(vocab, f['arr_0']))
    return embeddings_dict

import torch.optim as optim
import os
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from nltk import word_tokenize
from collections import namedtuple
import json
import os

class AverageMeter(object):
    """
    Keeps track of most recent, average, sum, and count of a metric.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def adjust_learning_rate(optimizer, scale_factor):
    """
    Shrinks learning rate by a specified factor.

    :param optimizer: optimizer whose learning rates must be decayed
    :param scale_factor: factor to scale by
    """

    print("\nDECAYING learning rate.")
    for param_group in optimizer.param_groups:
        param_group['lr'] = param_group['lr'] * scale_factor
    print("The new learning rate is %f\n" % (optimizer.param_groups[0]['lr'],))

def save_checkpoint(epoch, model, optimizer, save_checkpoint_path):
    """
    Save model checkpoint.

    :param epoch: epoch number
    :param model: model
    :param optimizer: optimizer
    :param save_checkpoint_path: path where to save the checkpoint
    """
    state = {'epoch': epoch,
             'model': model,
             'optimizer': optimizer,
             # 'word_map': word_map
             }
    filename = 'checkpoint_han_'+'epoch_'+str(epoch)+'.pth.tar'
    torch.save(state, os.path.join(save_checkpoint_path, filename))

def clip_gradient(optimizer, grad_clip):
    """
    Clip gradients computed during backpropagation to prevent gradient explosion.

    :param optimizer: optimized with the gradients to be clipped
    :param grad_clip: gradient clip value
    """
    for group in optimizer.param_groups:
        for param in group['params']:
            if param.grad is not None:
                param.grad.data.clamp_(-grad_clip, grad_clip)


def get_config(config_path):
    """
    Gets the config from a given path.
    :param config_path: the path to load the config from
    """
    with open(config_path) as config_file:
        config = json.load(config_file)

    return config


class AttrDict(dict):
    """
    Small class to allow accessing a dict in dot notation (e.g. my_dict.property instead of my_dict["property"]).
    Dicts can be cast to this class, e.g. attr_dict = AttrDict(my_dict)
    """
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def config_to_namedtuple(obj):
    """
    Converts a JSON file in Python dict format to an AttrDict that can be accessed using dot notation.
    :param obj: a JSON dict to be converted to an AttrDict.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = config_to_namedtuple(value)
        # return namedtuple('GenericDict', obj.keys())(**obj)
        return AttrDict(obj)
    elif isinstance(obj, list):
        return [config_to_namedtuple(item) for item in obj]
    else:
        return obj

