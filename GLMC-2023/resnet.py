import math
import torch
import torch.nn as nn

__all__ = ['ResNet', 'build_resnet', 'resnet_versions', 'resnet_configs']

# ResNetBuilder {{{

class ResNetBuilder(object):
    def __init__(self, config):
        self.config = config

    def conv(self, kernel_size, in_planes, out_planes, stride=1):
        if kernel_size == 3:
            conv = self.config['conv'](
                    in_planes, out_planes, kernel_size=3, stride=stride,
                    padding=1, bias=False)
        elif kernel_size == 1:
            conv = nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride,
                             bias=False)
        elif kernel_size == 7:
            conv = nn.Conv2d(in_planes, out_planes, kernel_size=7, stride=stride,
                             padding=3, bias=False)
        else:
            return None

        nn.init.kaiming_normal_(conv.weight,
                mode=self.config['conv_init'],
                nonlinearity='relu')

        return conv

    def conv3x3(self, in_planes, out_planes, stride=1):
        """3x3 convolution with padding"""
        c = self.conv(3, in_planes, out_planes, stride=stride)
        return c

    def conv1x1(self, in_planes, out_planes, stride=1):
        """1x1 convolution with padding"""
        c = self.conv(1, in_planes, out_planes, stride=stride)
        return c

    def conv7x7(self, in_planes, out_planes, stride=1):
        """7x7 convolution with padding"""
        c = self.conv(7, in_planes, out_planes, stride=stride)
        return c

    def batchnorm(self, planes):
        bn = nn.BatchNorm2d(planes)
        nn.init.constant_(bn.weight, 1)
        nn.init.constant_(bn.bias, 0)
    
        return bn

    def activation(self):
        return nn.ReLU(inplace=True)
        # return nn.PReLU()
        # return nn.LeakyReLU(0.1)
# ResNetBuilder }}}

# BasicBlock {{{
class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, builder, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = builder.conv3x3(inplanes, planes, stride)
        self.bn1 = builder.batchnorm(planes)
        self.relu = builder.activation()
        self.conv2 = builder.conv3x3(planes, planes)
        self.bn2 = builder.batchnorm(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        if self.bn1 is not None:
            out = self.bn1(out)

        out = self.relu(out)

        out = self.conv2(out)
        if self.bn2 is not None:
            out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out
# BasicBlock }}}

# Bottleneck {{{
class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, builder, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = builder.conv1x1(inplanes, planes)
        self.bn1 = builder.batchnorm(planes)
        self.conv2 = builder.conv3x3(planes, planes, stride=stride)
        self.bn2 = builder.batchnorm(planes)
        self.conv3 = builder.conv1x1(planes, planes * self.expansion)
        self.bn3 = builder.batchnorm(planes * self.expansion)
        self.relu = builder.activation()
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        if self.bn1 is not None:
            out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        if self.bn2 is not None:
            out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        if self.bn3 is not None:
            out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        
        out = self.relu(out)

        return out
# Bottleneck }}}

# ResNet {{{
class ResNet(nn.Module):
    def __init__(self, builder, block, layers, num_classes=1000):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = builder.conv7x7(3, 64, stride=2)
        self.bn1 = builder.batchnorm(64)
        self.relu = builder.activation()
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(builder, block, 64, layers[0])
        self.layer2 = self._make_layer(builder, block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(builder, block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(builder, block, 512, layers[3], stride=2)
        # self.conv2_x = self._make_layer(builder, block, 64, layers[0])
        # self.conv3_x = self._make_layer(builder, block, 128, layers[1], stride=2)
        # self.conv4_x = self._make_layer(builder, block, 256, layers[2], stride=2)
        # self.conv5_x = self._make_layer(builder, block, 512, layers[3], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        #added fc, head
        hidden_dim=256
        self.fc_cb = nn.Linear(512 * block.expansion, num_classes)
        self.contrast_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.projection_head = nn.Sequential(
            nn.Linear(512 * block.expansion, hidden_dim),
        )

    def _make_layer(self, builder, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            dconv = builder.conv1x1(self.inplanes, planes * block.expansion,
                                    stride=stride)
            dbn = builder.batchnorm(planes * block.expansion)
            if dbn is not None:
                downsample = nn.Sequential(dconv, dbn)    
            else:
                downsample = dconv

        layers = []
        layers.append(block(builder, self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(builder, self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x, train=False):
        x = self.conv1(x)
        if self.bn1 is not None:
            x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        # x = self.conv2_x(x)
        # x = self.conv3_x(x)
        # x = self.conv4_x(x)
        # x = self.conv5_x(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        if train is True:
            out = self.fc(x)
            out_cb = self.fc_cb(x)
            z = self.projection_head(x)
            p = self.contrast_head(z)
            return out, out_cb, z,p
        else:
            x = self.fc_cb(x)
            return x
# ResNet }}}


resnet_configs = {
        'classic' : {
            'conv' : nn.Conv2d,
            'conv_init' : 'fan_out',
            },
        'fanin' : {
            'conv' : nn.Conv2d,
            'conv_init' : 'fan_in',
            },
        }

resnet_versions = {
        'resnet18' : {
            'block' : BasicBlock,
            'layers' : [2, 2, 2, 2],
            'num_classes' : 1000,
            },
         'resnet34' : {
            'block' : BasicBlock,
            'layers' : [3, 4, 6, 3],
            'num_classes' : 1000,
            },
         'resnet50' : {
            'block' : Bottleneck,
            'layers' : [3, 4, 6, 3],
            'num_classes' : 1000,
            },
        'resnet101' : {
            'block' : Bottleneck,
            'layers' : [3, 4, 23, 3],
            'num_classes' : 1000,
            },
        'resnet152' : {
            'block' : Bottleneck,
            'layers' : [3, 8, 36, 3],
            'num_classes' : 1000,
            },
        }



def build_resnet(args, version, config, model_state=None):
    version = resnet_versions[version]
    config = resnet_configs[config]

    builder = ResNetBuilder(config)
    print("Version: {}".format(version))
    print("Config: {}".format(config))
    model = ResNet(builder, 
                   version['block'], 
                   version['layers'], 
                   args.num_classes)

    return model
