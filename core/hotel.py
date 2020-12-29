import os
import json
import random
import numpy as np
import tensorflow as tf
from dataset import DataProcessor, get_dataset


class HotelProcessor(DataProcessor):
    """
    Processor for the Hotel dataset. 
    """

    def get_train_examples(self, data_dir):
        return self._create_examples(
            self._read_tsv(os.path.join(data_dir, "train.tsv")))

    def get_dev_examples(self, data_dir):
        return self._create_examples(
            self._read_tsv(os.path.join(data_dir, "dev.tsv")))

    def get_labels(self):
        return ["0", "1"]

    def _create_examples(self, lines):
        examples = []
        num_classes = len(self.get_labels())
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            text = self._convert_to_unicode(line[2])
            label = int(self._convert_to_unicode(line[1]))
            # convert label to one-hot format
            one_hot_label = [0] * num_classes
            one_hot_label[label] = 1
            examples.append({"text": text, "label": one_hot_label})
        return examples


def get_hotel_dataset(data_dir, max_seq_length, word_threshold, balance=False):
    """
    Return tf datasets (train and dev) and language index
    for the hotel dataset.
    Assume train.tsv and dev.tsv are in the dir.
    """
    processor = HotelProcessor()
    train_examples = processor.get_train_examples(data_dir)
    dev_examples = processor.get_dev_examples(data_dir)
    print("Dataset: hotel Review")
    print("Training samples %d, Validation sampels %d" %
          (len(train_examples), len(dev_examples)))

    # check the label balance
    train_labels = np.array([0., 0.])
    for train_example in train_examples:
        train_labels += train_example["label"]
    print("Training data: %d positive examples, %d negative examples." %
          (train_labels[1], train_labels[0]))

    dev_labels = np.array([0., 0.])
    for dev_example in dev_examples:
        dev_labels += dev_example["label"]
    print("Dev data: %d positive examples, %d negative examples." %
          (dev_labels[1], dev_labels[0]))

    if balance == True:

        random.seed(12252018)

        print("Make the Training dataset class balanced.")
        # make the hotel dataset to be a balanced dataset
        min_examples = int(min(train_labels[0], train_labels[1]))
        pos_examples = []
        neg_examples = []

        for train_example in train_examples:
            if train_example["label"][0] == 1:
                neg_examples.append(train_example)
            else:
                pos_examples.append(train_example)

        assert (len(neg_examples) == train_labels[0])
        assert (len(pos_examples) == train_labels[1])

        if train_labels[0] >= train_labels[1]:
            # more negative examples
            neg_examples = random.sample(neg_examples, min_examples)
        else:
            # more positive examples
            pos_examples = random.sample(pos_examples, min_examples)

        assert (len(pos_examples) == len(neg_examples))
        train_examples = pos_examples + neg_examples
        print(
            "After balance training data: %d positive examples, %d negative examples."
            % (len(pos_examples), len(neg_examples)))

    return get_dataset(train_examples, dev_examples, max_seq_length,
                       word_threshold)


def read_tsv(input_file, quotechar=None):
    """Reads a tab separated value file."""
    with tf.gfile.Open(input_file, "r") as f:
        reader = csv.reader(f, delimiter="\t", quotechar=quotechar)
        lines = []
        for line in reader:
            lines.append(line)
        return lines
def get_hotel_annotation(annotation_path,
                        aspect,
                        max_seq_length,
                        word2idx,
                        neg_thres=0.4,
                        pos_thres=0.6):
    """
    Read annotation from json and 
    return tf datasets of the hotel annotation.
    fpath -- annotations.json
    aspects:
        0 -- appearance
        1 -- aroma
        2 -- palate
    rating >= 0.6 --> 1, rating <= 0.4 --> 0, other discarded.  
    Outputs:
        data -- (num_examples, max_seq_length).
        masks -- (num_examples, max_seq_length).
        labels -- (num_examples, num_classes) in a one-hot format.        
        rationales -- binary sequence (num_examples, sequence_length)    
    """
    data = []
    labels = []
    masks = []
    rationales = []
    num_classes = 2
    lines=read_tsv(annotation_path)
    processor = HotelProcessor()
    for i, line in enumerate(lines):
        if i==0:
            continue
        text_ = processor._convert_to_unicode(line[2]).split(" ")
        label_ = int(processor._convert_to_unicode(line[1]))
        rationale = [int(x) for x in 
                     processor._convert_to_unicode(line[3]).split(" ")]
        one_hot_label = [0] * num_classes
        one_hot_label[label_] = 1
        # process the text
        input_ids = []
        if len(text_) > max_seq_length:
            text_ = text_[0:max_seq_length]

        for word in text_:
            word = word.strip()
            try:
                input_ids.append(word2idx[word])
            except:
                # word is not exist in word2idx, use <unknown> token
                input_ids.append(word2idx["<unknown>"])
        # process mask
        # The mask has 1 for real word and 0 for padding tokens.
        input_mask = [1] * len(input_ids)

        # zero-pad up to the max_seq_length.
        while len(input_ids) < max_seq_length:
            input_ids.append(0)
            input_mask.append(0)

        assert (len(input_ids) == max_seq_length)
        assert (len(input_mask) == max_seq_length)

        # construct rationale
        binary_rationale = [0] * len(input_ids)
        for k in range(len(binary_rationale)):
            #print(k)
            if k < len(rationale):
                binary_rationale[k] = rationale[k] 

        data.append(input_ids)
        labels.append(one_hot_label)
        masks.append(input_mask)
        rationales.append(binary_rationale)

    data = np.array(data, dtype=np.int32)
    labels = np.array(labels, dtype=np.int32)
    masks = np.array(masks, dtype=np.int32)
    rationales = np.array(rationales, dtype=np.int32)

    label_dis = np.sum(labels, axis=0)
    print("Annotated rationales: %d" % data.shape[0])
    print("Annotated data: %d positive examples, %d negative examples." %
          (label_dis[1], label_dis[0]))

    annotated_dataset = tf.data.Dataset.from_tensor_slices(
        (data, masks, labels, rationales))

    return annotated_dataset
