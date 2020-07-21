import time
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
import torch.optim as optim
from utils import *
from dataset import BertTwitterDataset
from torch.utils.tensorboard import SummaryWriter
import json
import click
import os
import copy
import numpy as np
import pandas as pd
from embeddings import *


def predict(eval_loader, model, device, config, prepare_embeddings_fn, embedder):
    model.eval()  # eval mode disables dropout
    results = np.array([])
    # Batches
    for i, data in enumerate(eval_loader):
        embeddings = prepare_embeddings_fn(data, embedder, device, config)

        # Forward prop.
        output = model(embeddings)

        # Find accuracy
        _, predictions = output["logits"].max(dim=1)  # (n_documents)
        results = np.concatenate((results, predictions.cpu().numpy()))
        print(i)

        try:
            for sentence in data:
                sentence.clear_embeddings()
        except:
            pass
    return results


@click.command()
@click.option('--config', default='specify_config_using_--config_option', type=str)
@click.option('--checkpoint', default='specify_checkpoint_using_--checkpoint_option', type=str)
@click.option('--predict-file', default='./prediction', type=str)
@click.option('--embedding', default='specify_embedding_using_--embedding_option', type=str)


def main_cli(config, checkpoint, predict_file, embedding):
    # Dataset parameters
    config_dict = get_config(config)
    config = config_to_namedtuple(config_dict)

    batch_size = 8
    dataset_path = config.dataset.dataset_dir
    test_file_path = config.dataset.rel_test_path
    sentence_length_cut = config.model.sentence_length_cut #set fixed sentence length
    workers = config.training.workers  # number of workers for loading data in the DataLoader
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # setup embeddings
    
    embedder = initialize_embeddings(embedding, device, fine_tune_embeddings=fine_tune_embeddings)
    if embedding in ["flair", "bert", "elmo"]:
        import flair
        from flair.datasets import CSVClassificationDataset
        print("[flair] initializing dataset", flush=True)
        eval_dataset = CSVClassificationDataset(os.path.join(dataset_path, test_file_path), {1: "text", 2: "label"}, max_tokens_per_doc=sentence_length_cut, tokenizer=False, in_memory=False, skip_header=True)
        eval_loader = flair.datasets.DataLoader(eval_dataset, batch_size=batch_size, shuffle=False, num_workers=workers)
        prepare_embeddings_fn = prepare_embeddings_flair
        print("[flair] entering prediction loop", flush=True)
    
    elif embedding in ["bert-mix", "bert-base", "bert-last-four"]:
        print(f"[{embedding}] initializing embeddings+dataset", flush=True)
        eval_dataset = BertTwitterDataset(csv_file=os.path.join(dataset_path, test_file_path))
        eval_loader = torch.utils.data.DataLoader(eval_dataset, batch_size=batch_size, num_workers=workers, shuffle=False)  # should shuffle really be false? copying from the notebook
        prepare_embeddings_fn = eval("prepare_embeddings_" + embedding.replace("-", "_"))
        print(f"{embedding} entering prediction loop", flush=True)

    else:
        raise NotImplementedError("Unsupported embedding: " + embedding)

    checkpoint = torch.load(checkpoint)
    model = checkpoint['model']
    if hasattr(model, "embedder"):
        print("Model has built-in embedder, using it", flush=True)
        embedder = model.embedder
    else:
        print("Using user-defined embedder", flush=True)

    results = predict(eval_loader, model, device, config, prepare_embeddings_fn, embedder)
    results = ((results-0.5)*2)
    sub = pd.read_csv("./sample_submission.csv", index_col=False)
    sub["Prediction"] = results.astype(int)
    sub.to_csv(predict_file, index=False)


if __name__ == '__main__':
    main_cli()
