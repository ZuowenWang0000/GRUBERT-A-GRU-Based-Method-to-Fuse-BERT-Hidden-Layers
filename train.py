import time
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
import torch.optim as optim
from attention_network import AttentionNetwork
from lstm_model import LstmModel
from dataset import TweetsDataset
from utils import *
import json
import click
import os
import copy
from test import test
from load_embeddings import *
from torch.utils.tensorboard import SummaryWriter
import tensorflow_hub as hub
import os
# os.environ["CUDA_VISIBLE_DEVICES"]="-1"
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# import tensorflow as tf
import tensorflow.compat.v1 as tf
tf.disable_eager_execution()
import sys

def main(config, save_checkpoint_path, seed=None):
    """
    Training and validation.
    """
    global checkpoint, start_epoch
    # get configs
    config_dict = get_config(config)
    config = config_to_namedtuple(config_dict)

    torch.manual_seed(seed)
    np.random.seed(seed)

    print(config)
    # embedding parameters , the center of our study
    emb_sizes_list = config.embeddings.emb_sizes_list

    # Model parameters
    if config.model.architecture == "attention":
        print("using attention model")
        model_type = AttentionNetwork
    elif config.model.architecture == "lstm":
        print("using lstm model")
        model_type = LstmModel
    else:
        raise NotImplementedError
    n_classes = config.model.n_classes
    word_rnn_size = config.model.word_rnn_size  # word RNN size
    word_rnn_layers = config.model.word_rnn_layers  # number of layers in character RNN
    word_att_size = config.model.word_att_size  # size of the word-level attention layer (also the size of the word context vector)
    dropout = config.model.dropout  # dropout
    fine_tune_word_embeddings = config.model.fine_tune_word_embeddings  # fine-tune word embeddings?
    sentence_length_cut = config.model.sentence_length_cut #set fixed sentence length

    # Training parameters
    start_epoch = config.training.start_epoch  # start at this epoch
    batch_size = config.training.batch_size  # batch size
    lr = config.training.lr  # learning rate
    momentum = config.training.momentum  # momentum
    workers = config.training.workers  # number of workers for loading data in the DataLoader
    epochs = config.training.epochs  # number of epochs to run
    checkpoint = config.training.checkpoint  # path to saved model checkpoint, None if none
    save_checkpoint_freq_epoch = config.training.save_checkpoint_freq_epoch
    train_without_val = config.training.train_without_val
    save_checkpoint_path = config.training.save_checkpoint_path

    # Dataset parameters
    dataset_path = config.dataset.dataset_dir
    train_file_path = config.dataset.rel_train_path
    val_file_path = config.dataset.rel_val_path
    test_file_path = config.dataset.rel_test_path

    cudnn.benchmark = False  # set to true only if inputs to model are fixed size; otherwise lot of computational overhead


    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Initialize model or load checkpoint
    if checkpoint!="None":
        checkpoint = torch.load(checkpoint)
        model = checkpoint['model']
        optimizer = checkpoint['optimizer']
        # word_map = checkpoint['word_map']
        start_epoch = checkpoint['epoch'] + 1
        print(
            '\nLoaded checkpoint from epoch %d.\n' % (start_epoch - 1))
    else:
        model = model_type(n_classes=n_classes,
                                 emb_sizes_list=emb_sizes_list,
                                 word_rnn_size=word_rnn_size,
                                 word_rnn_layers=word_rnn_layers,
                                 word_att_size=word_att_size,
                                 dropout=dropout,
                                 device=device)

        # model.sentence_attention.word_attention.fine_tune_embeddings(fine_tune_word_embeddings)  # fine-tune
        optimizer = optim.Adam(params=filter(lambda p: p.requires_grad, model.parameters()), lr=lr)

    # Loss functions
    criterion = nn.CrossEntropyLoss()

    # Move to device
    model = model.to(device)
    criterion = criterion.to(device)

    words_to_embed = "dog cat sloth"  # <-- it's a list now, and the name changed

    # elmo = hub.Module("https://tfhub.dev/google/elmo/3")
    # sess = tf.Session()
    # sess.run(tf.global_variables_initializer())
    # elmoEmbedding = ElmoEmbedding(elmo, sess)
    # embedding = elmoEmbedding.embed(words_to_embed, sess)
    # embedding = sess.run(embedding_tensor)
    # print(embedding.shape)


    glove_embedding = GloveEmbedding(dataset_path, train_file_path, val_file_path, sentence_length_cut)
    syngcn_embedding = SynGcnEmbedding(dataset_path, train_file_path, val_file_path, sentence_length_cut, "../embeddings/syngcn_embeddings.txt")


    # DataLoaders
    train_loader = torch.utils.data.DataLoader(TweetsDataset(glove_embedding.get_train_set(), syngcn_embedding.get_train_set()),
                                               batch_size=batch_size, shuffle=True,
                                               num_workers=workers, pin_memory=True)
    #    validation
    val_loader = torch.utils.data.DataLoader(TweetsDataset(glove_embedding.get_test_set(), syngcn_embedding.get_test_set()),
                                               batch_size=batch_size, shuffle=True,
                                               num_workers=workers, pin_memory=True)

    # set up tensorboard writer
    writer = SummaryWriter(save_checkpoint_path)

    # writer.add_graph(model)

    # initialzie elmo
    sess = tf.Session()
    elmo = hub.Module("https://tfhub.dev/google/elmo/3")
    sess.run(tf.global_variables_initializer())
    elmoEmbedding = ElmoEmbedding(elmo, sess)

    # Epochs
    train_start_time = time.time()
    for epoch in range(start_epoch, epochs):
        epoch_start = time.time()
        # One epoch's training
        train(train_loader=train_loader,
              model=model,
              criterion=criterion,
              optimizer=optimizer,
              epoch=epoch,
              device=device,
              config=config,
              tf_writer=writer,
              elmo = elmoEmbedding)

        # Decay learning rate every epoch
        adjust_learning_rate(optimizer, 0.99)

        # Save checkpoint
        if epoch % save_checkpoint_freq_epoch == 0:
            save_checkpoint(epoch, model, optimizer, save_checkpoint_path)
            if not train_without_val:
                test(val_loader, model, criterion, device, config, writer, epoch)
        epoch_end = time.time()
        print("per epoch time = {}".format(epoch_end-epoch_start))
        sys.stdout.flush()

    train_end_time = time.time()
    print("Total training time : {} minutes".format((train_end_time-train_start_time)/60.0))

    print("Final evaluation:")
    test(val_loader, model, criterion, device, config, writer, epoch)
    writer.close()


def train(train_loader, model, criterion, optimizer, epoch, device, config, tf_writer, elmo):
    """
    Performs one epoch's training.

    :param train_loader: DataLoader for training data
    :param model: model
    :param criterion: cross entropy loss layer
    :param optimizer: optimizer
    :param epoch: epoch number
    """

    model.train()  # training mode enables dropout

    batch_time = AverageMeter()  # forward prop. + back prop. time per batch
    data_time = AverageMeter()  # data loading time per batch
    losses = AverageMeter()  # cross entropy loss
    accs = AverageMeter()  # accuracies

    start = time.time()

    # Batches
    length = config.model.sentence_length_cut
    for i, (data, tweet) in enumerate(train_loader):
        batch_start = time.time()
        # embeddings = torch.tensor(data["embeddings"])
        embeddings = data["embeddings"]
        labels = data["label"]
        embeddings = embeddings.to(device)
        labels = labels.to(device)  # (batch_size)

        data_time.update(time.time() - start)

        # for j in range(len(tweet)):
        #     print(tweet[j][1])
        # print(np.array(tweet).T[0])
        # print(np.array(tweet).T[1])
        # print(np.array(tweet).T[2])


        elmo_embeddings = torch.Tensor(elmo.embed(np.array(tweet).T, [length for _ in range(len(labels))])).to(device)
        # print(elmo_embeddings.shape)

        embeddings = torch.cat([embeddings, elmo_embeddings], 2)
        batch_load = time.time()

        # print(embeddings.shape)

        print("batch load time:{}".format(batch_load - batch_start))
        # Forward prop.
        scores, word_alphas, emb_weights = model(embeddings)

        if config.embeddings.use_regularization == "none":
            loss = criterion(scores.to(device), labels)
        elif config.embeddings.use_regularization == "l1":
            # Regularization on embedding weights
            emb_weights_norm = torch.norm(model.emb_weights, p=1)
            # Loss
            loss = criterion(scores.to(device), labels) + config.embeddings.l1_lambda * emb_weights_norm  # scalar
        else:
            raise NotImplementedError

        # Back prop.
        optimizer.zero_grad()
        loss.backward()

        # print(model.emb_weights.grad)

        # Clip gradients

        if config.training.grad_clip!="None":
            clip_gradient(optimizer, config.grad_clip)

        # Update
        optimizer.step()

        # Find accuracy
        _, predictions = scores.max(dim=1)  # (n_documents)
        correct_predictions = torch.eq(predictions, labels).sum().item()
        accuracy = correct_predictions / labels.size(0)

        # Keep track of metrics
        losses.update(loss.item(), labels.size(0))
        batch_time.update(time.time() - start)
        accs.update(accuracy, labels.size(0))

        start = time.time()

        # Print training status
        if i % config.training.print_freq == 0:
            print('Epoch: [{0}][{1}/{2}]\t'
                  'Batch Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Data Load Time {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Accuracy {acc.val:.3f} ({acc.avg:.3f})'.format(epoch, i, len(train_loader),
                                                                  batch_time=batch_time,
                                                                  data_time=data_time, loss=losses,
                                                                  acc=accs))
        batch_end = time.time()
        print("batch time :{}".format(batch_end - batch_start))
    # ...log the running loss, accuracy
    print("***writing to tf board")
    tf_writer.add_scalar('training loss (avg. epoch)', losses.avg, epoch)
    tf_writer.add_scalar('training accuracy (avg. epoch)', accs.avg, epoch)
    tf_writer.add_scalar('learning rate', optimizer.param_groups[0]['lr'], epoch)



@click.command()
@click.option('--config', default='configs/pipeline_check_lstm.json', type=str)
@click.option('--save-checkpoint-path', default='./log_dir/')
@click.option('--seed', default=0, type=int)

def main_cli(config, save_checkpoint_path, seed):
    main(config, save_checkpoint_path, seed)


if __name__ == '__main__':
    main_cli()
