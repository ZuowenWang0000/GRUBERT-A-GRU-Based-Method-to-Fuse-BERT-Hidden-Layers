from __future__ import print_function, division
import os
import torch
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer


class BertTwitterDataset(Dataset):
    """Twitter dataset."""

    def __init__(self, csv_file=None, tweet_data_frame=None, transform=None, sentence_length_cut=40):
        """
        Args:
            csv_file (string): Path to the csv file with twitter files.
            transform (callable, optional): Optional transform to be applied
                on a sample.
        """
        if csv_file is not None:
          self.tweet_data_frame = pd.read_csv(csv_file)
        elif tweet_data_frame is not None:
          self.tweet_data_frame = tweet_data_frame
        else:
          #abcd
          pass

        self.transform = transform

        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

        self.tweets = self.tweet_data_frame['text']
        self.labels = self.tweet_data_frame['label']
        self.tweet_list = self.sentences_from_df()
        self.tokenized_tweets = torch.LongTensor(self.tokenize_sentences(self.tweet_list, self.tokenizer, max_seq_len=sentence_length_cut))


    def __len__(self):
        return len(self.tweet_data_frame)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

   
        tweet = self.tokenized_tweets[idx]
        label = self.labels[idx]
        sample = {'text': tweet, 'label': label}

        if self.transform:
            sample = self.transform(sample)

        return sample

    def sentences_from_df(self):
        sentences = []
        for i in range(len(self.tweets)):
          sentences.append(str(self.tweets.loc[i]))
        return sentences

    def tokenize_sentences(self,sentences, tokenizer, max_seq_len=40):
      """Encode sentences for using with BERT"""
      tokenized_sentences = []

      for sentence in sentences:
          tokenized_sentence = tokenizer.encode(
                              sentence,                  # Sentence to encode.
                              max_length = max_seq_len,  # Truncate all sentences.
                              pad_to_max_length=True,    # padding with zeros
                              truncation=True
                      )
          tokenized_sentences.append(tokenized_sentence)

      return tokenized_sentences
