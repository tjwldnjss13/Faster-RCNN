import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader

from coco_dataset import COCODataset, collate_fn_bbox
from model import FasterRCNN
from rpn import anchor_box_generator, anchor_label_generator, anchor_label_generatgor_2dim, \
                anchor_ground_truth_generator, loc_delta_generator
from loss import rpn_reg_loss, rpn_cls_loss
from torchsummary import summary

if __name__ == '__main__':
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    learning_rate = .00001
    batch_size = 8
    epoch = 20

    ########## For Real Training ##########
    root = ''

    root_train = os.path.join(root, 'images', 'train')
    root_val = os.path.join(root, 'images', 'val')

    ann_train = os.path.join(root, 'annotations', 'instances_train2017.json')
    ann_val = os.path.join(root, 'annotations', 'instances_val2017.json')

    transform = transforms.Compose([transforms.Resize((600, 1000), transforms.ToTensor())])

    dset_train = COCODataset(root_train, ann_train, transform)
    dset_val = COCODataset(root_val, ann_val, transform)

    train_data_loader = DataLoader(dset_train, batch_size=batch_size, shuffle=True, collate_fn=collate_fn_bbox)
    val_data_loader = DataLoader(dset_val, batch_size=batch_size, shuffle=True, collate_fn=collate_fn_bbox)

    n_train_data = train_data_loader.__len__()
    n_val_data = val_data_loader.__len__()

    in_size = (600, 1000)
    model = FasterRCNN(in_size, 91, False).to(device)

    ratios = [.5, 1, 2]
    scales = [128, 256, 512]
    anchor_boxes = anchor_box_generator(ratios, scales, in_size, 16)
    idx_valid_ = np.where((anchor_boxes[:, 0] >= 0) &
                                 (anchor_boxes[:, 1] >= 0) &
                                 (anchor_boxes[:, 2] <= in_size[0]) &
                                 (anchor_boxes[:, 3] <= in_size[1]))[0]
    anchor_boxes = anchor_boxes[idx_valid_]


    ########## For Real Training ##########

    backbone = model.backbone
    rpn = model.rpn
    rpn_optimizer = optim.SGD(rpn.parameters(), lr=learning_rate)

    # reg_losses, cls_losses = [], []

    for e in range(epoch):
        for i, (images, bboxes) in enumerate(train_data_loader):
            n_batch = len(images)
            print('[{}/{}] {}/{} '.format(e + 1, epoch, (i + 1) * n_batch, n_train_data), end='')

            x_ = images
            y_ = bboxes

            rpn_optimizer.zero_grad()
            backbone_feature = model.backbone(x_)
            reg, cls = rpn(backbone_feature)

            anchor_labels_ = anchor_label_generator(anchor_boxes, gt_numpy, .7, .3)
            anchor_labels2_ = anchor_label_generatgor_2dim(anchor_labels_)
            anchor_gts_ = anchor_ground_truth_generator(anchor_boxes, gt)
            anchor_gts_ = loc_delta_generator(anchor_gts_, anchor_boxes)

            idx_valid = torch.LongTensor(idx_valid_).to(device)
            anchor_labels_ = torch.Tensor(anchor_labels_).to(device)
            anchor_labels2_ = torch.Tensor(anchor_labels2_).to(device)
            anchor_gts_ = torch.Tensor(anchor_gts_).to(device)

            anchor_labels = anchor_labels_[idx_valid]
            anchor_labels2 = anchor_labels2_[idx_valid]
            anchor_gts = anchor_gts_[idx_valid]

            del gt
            del idx_valid_
            del anchor_labels_
            del anchor_labels2_
            del anchor_gts_

            n_reg, reg_loss = rpn_reg_loss(reg[:, idx_valid], anchor_gts, anchor_labels)
            n_cls, cls_loss = rpn_cls_loss(cls[:, idx_valid], anchor_labels2, anchor_labels)

            lambda_ = n_reg / n_cls
            # reg_loss.backward(retain_graph=True)
            # cls_loss.backward(retain_graph=True)
            loss = cls_loss + lambda_ * reg_loss
            loss.backward(retain_graph=True)
            rpn_optimizer.step()

            # reg_losses.append(reg_loss)
            # cls_losses.append(cls_loss)

        print('<loss> {} <reg_loss> {} <cls_loss> {}'.format(loss, reg_loss, cls_loss))

    # plt.figure(0)
    # plt.title('Reg/Cls Loss')
    # plt.plot([i for i in range(epoch)], reg_loss, label='Reg')
    # plt.plot([i for i in range(epoch)], cls_loss, label='Cls')
    # plt.legend()
    # plt.show()



        # for i, data in enumerate(train_data_loader):
        # backbone_feature = faster_rcnn_model.backbone(image)
        # reg, cls = faster_rcnn_model.rpn(backbone_feature)

    ########## Visualize ##########
    # import copy

    # img_copy = copy.deepcopy(img_numpy)

    # pos_args_label = np.where(anchor_labels == 1)
    # neg_args_label = np.where(anchor_labels == -1)
    # pos_boxes = anchor_boxes[pos_args_label]
    # neg_boxes = anchor_boxes[neg_args_label]

    # print(pos_boxes.shape, neg_boxes.shape)

    # pos_box = pos_boxes[-1]
    # y1, x1, y2, x2 = int(pos_box[0]), int(pos_box[1]), int(pos_box[2]), int(pos_box[3])
    # cv.rectangle(img_copy, (x1, y1), (x2, y2), (0, 0, 255), 3)

    # y1, x1, y2, x2 = int(bbox_numpy[2][0]), int(bbox_numpy[2][1]), int(bbox_numpy[2][2]), int(bbox_numpy[2][3])
    # cv.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 3)

    # neg_box = neg_boxes[-1]
    # y1, x1, y2, x2 = int(neg_box[0]), int(neg_box[1]), int(neg_box[2]), int(neg_box[3])
    # cv.rectangle(img_copy, (x1, y1), (x2, y2), (255, 0, 0), 3)

    # plt.figure(figsize=(5, 5))
    # plt.imshow(img_copy)
    # plt.show()

    print('Done')

