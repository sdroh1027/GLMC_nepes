import torchvision
import random
from torch.utils.data import Dataset, DataLoader
import numpy as np
from PIL import Image
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

import os
import collections
from typing import Callable, Tuple
import pickle

import albumentations
import torchvision.transforms as transforms
import torch
import pdb

import sys
sys.path.insert(0, '/home/esoc/jihee/GLMC_nepes/GLMC-2023/imbalance_data')

from albumentations import (
    Normalize,
    Blur,
    GridDistortion,
    ElasticTransform,
    ColorJitter,
    ShiftScaleRotate,
    Transpose,
    RandomRotate90,
    Sharpen,
    MedianBlur,
    MultiplicativeNoise,
    JpegCompression,
    RandomGridShuffle,
    Resize,
    #ToTensor,
    CenterCrop,
)


def create_dataset(args, data_root, is_train: bool, transform):
    separated_train_val = 'train' in os.listdir(data_root)
    if separated_train_val:
        classes_list = os.listdir(data_root + '/train')
        classes_list.sort()
        data_root_train = data_root + '/train'
        if args.use_eval:
            data_root_valid = data_root + '/eval'
        else:
            data_root_valid = data_root + '/valid'
    else:
        classes_list = os.listdir(data_root)
    for c in classes_list:
        if c[0] == '.':
            classes_list.remove(c)
    classes = {name: i for i, name in enumerate(classes_list)}

    #class 개수 초기화
    args.num_classes = len(classes)
    #train_transform = create_nepes_transform(args, is_train=True)
    #val_transform = create_nepes_transform(args, is_train=False)
    
    if not os.path.exists(args.save_path):
        os.makedirs(args.save_path, exist_ok=True)
    #path = args.save_path + '/train_val_lists.p'

    if True:
        #assert os.path.isfile(path) is False, 'ERROR: you are trying to reset file \'train_val_lists.p\'. this will mess up the whole experiment.' \
        #                                      ' if you want to resume from checkpoint without resetting, please add \'train.resume True\' in command when running. ' \
        #                                      'if you want to start a new experiment, please remove whole dir or use other dir name'
        train_list, val_list, num_data = [], [], []
        if separated_train_val:
            for c in classes.keys():
                file_list_train = os.listdir(os.path.join(data_root_train, c))
                file_list_valid = os.listdir(os.path.join(data_root_valid, c))
                for s in file_list_train:
                    if not s.endswith('.jpg'):
                        print('\'{}\' is removed from dataset'.format(os.path.join(data_root_train, c, s)))
                        file_list_train.remove(s)
                for s in file_list_valid:
                    if not s.endswith('.jpg'):
                        print('\'{}\' is removed from dataset'.format(os.path.join(data_root_train, c, s)))
                        file_list_valid.remove(s)
                length = len(file_list_train) + len(file_list_valid)
                num_data.append(length)
                train_list += [(os.path.join(data_root_train, c, f), classes[c]) for f in file_list_train]
                val_list += [(os.path.join(data_root_valid, c, f), classes[c]) for f in file_list_valid]
        else:
            # separate dataset manually
            for c in classes.keys():
                file_list = os.listdir(os.path.join(data_root, c))
                for s in file_list:
                    if not s.endswith('.jpg'):
                        print('\'{}\' is removed from dataset'.format(os.path.join(data_root_train, c, s)))
                        file_list.remove(s)
                np.random.seed(0)
                np.random.shuffle(file_list)
                length = len(file_list)
                num_data.append(length)
                train_list += [(os.path.join(data_root, c, f), classes[c]) for f in file_list[:int(0.9*length)]]
                val_list += [(os.path.join(data_root, c, f), classes[c]) for f in file_list[int(0.9*length):]]

        #datapath_dict = {'train': train_list, 'val': val_list, 'class_name': classes_list, 'num_data_cls': num_data}
        args.num_data_cls = num_data
        args.class_name = classes_list
        #with open(path, 'wb') as file:
        #    pickle.dump(datapath_dict, file)

    #train_list: [(-.jpg, class label) (-.jpg, class label) ...]

    if is_train:
        train_dataset = BasicDataset(args, train_list, transform)
        #val_dataset = BasicDataset(args, val_list, val_transform)
        return train_dataset #, val_dataset
    else:
        val_dataset = BasicDataset(args, val_list, transform)
        return val_dataset


class BasicDataset(Dataset):
    def __init__(self, args, path_list, transform=None):
        super(BasicDataset, self).__init__()
        self.path_list = path_list
        self.transform = transform
        self.args = args
        self.targets = []

        data_list = []
        if len(self.path_list) < 10000 and False:
            # if the size of dataset is small, load all of them for faster speed
            for i in range(len(self.path_list)):
                img, c = self.path_list[i]
                img = Image.open(img)
                data_list.append((img, c))
                self.targets.append(c)
            self.data_list = data_list
        else:
            # if the size of dataset is big, load a batch at each iteration
            self.data_list = None
            for i in range(len(self.path_list)):
                img, c = self.path_list[i]
                #img = Image.open(img)
                #data_list.append((img, c))
                self.targets.append(c)
        
        class_list = np.zeros(args.num_classes)
        for i in range(len(self.path_list)):
            _, c = self.path_list[i]
            class_list[c]+=1
        self.class_list = class_list
        print("per class num: {}".format(class_list))
            

    def __getitem__(self, index):
        if self.data_list:
            img, c = self.data_list[index]
        else:
            path, c = self.path_list[index]
            img = Image.open(path) #<class 'PIL.Image.Image'>

        if self.transform:
            img = self.transform(img) #type(img): dict, img['image'].shape: (256, 256, 3), ndarray type
        return img, c

    def __len__(self):
        return len(self.path_list)
    
    def get_per_class_num(self):
        return self.class_list


def create_nepes_transform(args, is_train: bool) -> Callable:
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    if is_train:
        transforms = []
        if args.augmentation == "blur":
            transforms.append(Blur(args))
        if args.augmentation == "grid_distortion":
            transforms.append(GridDistortion(args))
        if args.augmentation == "use_elastic_transform":
            transforms.append(ElasticTransform(args))
        if args.augmentation == "colorjitter":
            transforms.append(ColorJitter(args))
        if args.augmentation == "shiftscale_rotate":
            transforms.append(ShiftScaleRotate(args))
        if args.augmentation == "use_transpose":
            transforms.append(Transpose(args))
        if args.augmentation == "random_rotate90":
            transforms.append(RandomRotate90(args))
        if args.augmentation == "sharpen":
            transforms.append(Sharpen(args))
        if args.augmentation == "medianblur":
            transforms.append(MedianBlur(args))
        if args.augmentation == "multiplicative_noise":
            transforms.append(MultiplicativeNoise(args))
        if args.augmentation == "jpegcompression":
            transforms.append(JpegCompression(args))   
        if args.augmentation == "randomgrid_shuffle":
            transforms.append(RandomGridShuffle(args))
        #if args.use_resize:
        #    transforms.append(Resize(args))
        #if args.use_center_crop:
        #    transforms.append(CenterCrop(args))

        # transforms.append(Normalize(mean, std))
        #transforms.append(ToTensor())  # erase in albumentations

    else:
        transforms = []
        #if args.use_resize:
        #    transforms.append(Resize(args))
        transforms += [
             # Normalize(mean, std),
             #ToTensor()  # erase in albumentations
         ]

    return albumentations.Compose(transforms)