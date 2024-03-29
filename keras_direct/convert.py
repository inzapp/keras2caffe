import caffe 
from caffe import layers as L, params as P

import math
import numpy as np
import tensorflow as tf


def set_padding(config_keras, input_shape, config_caffe):
    if config_keras['padding']=='valid':
        #config_caffe['pad'] = 1
        return
    elif config_keras['padding']=='same':
        #pad = ((layer.output_shape[1] - 1)*strides[0] + pool_size[0] - layer.input_shape[1])/2
        #pad=pool_size[0]/(strides[0]*2)
        #pad = (pool_size[0]*layer.output_shape[1] - (pool_size[0]-strides[0])*(layer.output_shape[1]-1) - layer.input_shape[1])/2
        
        if 'kernel_size' in config_keras:
            kernel_size = config_keras['kernel_size']
        elif 'pool_size' in config_keras:
            kernel_size = config_keras['pool_size']
        else:
            raise Exception('Undefined kernel size')
        
        #pad_w = int(kernel_size[1] // 2)
        #pad_h = int(kernel_size[0] // 2)
        
        strides = config_keras['strides']
        w = input_shape[1]
        h = input_shape[2]
        
        out_w = math.ceil(w / float(strides[1]))
        pad_w = int((kernel_size[1]*out_w - (kernel_size[1]-strides[1])*(out_w - 1) - w)/2)
        
        out_h = math.ceil(h / float(strides[0]))
        pad_h = int((kernel_size[0]*out_h - (kernel_size[0]-strides[0])*(out_h - 1) - h)/2)
        if pad_w==0 and pad_h==0:
            return
        if pad_w==pad_h:
            config_caffe['pad'] = pad_w
        else:
            config_caffe['pad_h'] = pad_h
            config_caffe['pad_w'] = pad_w
    else:
        raise Exception(config_keras['padding']+' padding is not supported')


def convert(keras_model, caffe_net_file, caffe_params_file):
    caffe_net = caffe.NetSpec()
    net_params = dict()
    outputs=dict()
    shape=()
    input_str = ''
    for layer in keras_model.layers:
        name = layer.name
        layer_type = type(layer).__name__
        config = layer.get_config()
        blobs = layer.get_weights()
        blobs_num = len(blobs)
        
        # with open('caffe_kernel.txt', 'a') as f:
        #     f.write(str(blobs))

        print('input_layer: ', name)
        if type(layer.output) == list:
            raise Exception('Layers with multiply outputs are not supported')
        else: 
            top=layer.output.name
            print('TOP: ',top)
        
        if type(layer.input) != list:
            bottom = layer.input.name
            print('Bottom: ',bottom)

        if layer_type == 'InputLayer' or len(caffe_net.tops) == 0:
            input_name = 'x'
            caffe_net[input_name] = L.Layer()
            input_shape = config['batch_input_shape']
            input_str = 'input: {}\ninput_dim: {}\ninput_dim: {}\ninput_dim: {}\ninput_dim: {}'.format('"' + input_name + '"',
                1, input_shape[3], input_shape[1], input_shape[2])
            outputs[layer.input.name] = input_name
            if layer_type == 'InputLayer':
                continue
        if layer_type == 'Conv2D' or layer_type == 'Convolution2D':
            strides = config['strides']
            kernel_size = config['kernel_size']
            kwargs = { 'num_output': config['filters'] }
            if kernel_size[0] == kernel_size[1]:
                kwargs['kernel_size']=kernel_size[0]
            else:
                kwargs['kernel_h']=kernel_size[0]
                kwargs['kernel_w']=kernel_size[1]
            
            if strides[0]==strides[1]:
                kwargs['stride']=strides[0]
            else:
                kwargs['stride_h']=strides[0]
                kwargs['stride_w']=strides[1]
            
            if not config['use_bias']:
                kwargs['bias_term'] = False
                kwargs['param']=[dict(lr_mult=0)]
            else:
                # kwargs['param']=[dict(lr_mult=0), dict(lr_mult=0)]
                kwargs['bias_term'] = True
            
            set_padding(config, layer.input_shape, kwargs)
            print(kwargs)
            caffe_net[name] = L.Convolution(caffe_net[outputs[bottom]], **kwargs)

            blobs[0] = np.array(blobs[0]).transpose(3,2,0,1)
            # blobs[1] = np.zeros(np.array(blobs[1]).shape)
            net_params[name] = blobs

            if config['activation'] == 'relu':
                name_s = name+'s'
                caffe_net[name_s] = L.ReLU(caffe_net[name], in_place=True)
            elif config['activation'] == 'sigmoid':
                name_s = name+'s'
                caffe_net[name_s] = L.Sigmoid(caffe_net[name], in_place=True)
            elif config['activation'] == 'linear':
                pass  # do nothing
            else:
                raise Exception('Unsupported activation '+config['activation'])
        elif layer_type == 'DepthwiseConv2D':
            strides = config['strides']
            kernel_size = config['kernel_size']
            kwargs = {'num_output': layer.input_shape[3]}

            if kernel_size[0] == kernel_size[1]:
                kwargs['kernel_size'] = kernel_size[0]
            else:
                kwargs['kernel_h'] = kernel_size[0]
                kwargs['kernel_w'] = kernel_size[1]

            if strides[0] == strides[1]:
                kwargs['stride'] = strides[0]
            else:
                kwargs['stride_h'] = strides[0]
                kwargs['stride_w'] = strides[1]

            set_padding(config, layer.input_shape, kwargs)
            kwargs['group'] = layer.input_shape[3]
            kwargs['bias_term'] = False
            caffe_net[name] = L.Convolution(caffe_net[outputs[bottom]], **kwargs)
            blob = np.array(blobs[0]).transpose(2, 3, 0, 1)
            blob.shape = (1,) + blob.shape
            net_params[name] = blob
            
            if config['activation'] == 'relu':
                name_s = name + 's'
                caffe_net[name_s] = L.ReLU(caffe_net[name], in_place=True)
            elif config['activation'] == 'LeakyReLU':
                name_s = name+'s'
                caffe_net[name_s] = L.ReLU(caffe_net[name], in_place=True,negative_slope=round(0.1,1))
            elif config['activation'] == 'sigmoid':
                name_s = name+'s'
                caffe_net[name_s] = L.Sigmoid(caffe_net[name], in_place=True)
            elif config['activation'] == 'linear':
                pass  # do nothing
            else:
                raise Exception('Unsupported activation '+config['activation'])
        elif layer_type == 'SeparableConv2D':
            strides = config['strides']
            kernel_size = config['kernel_size']
            kwargs = {'num_output': layer.input_shape[3]}

            if kernel_size[0] == kernel_size[1]:
                kwargs['kernel_size'] = kernel_size[0]
            else:
                kwargs['kernel_h'] = kernel_size[0]
                kwargs['kernel_w'] = kernel_size[1]

            if strides[0] == strides[1]:
                kwargs['stride'] = strides[0]
            else:
                kwargs['stride_h'] = strides[0]
                kwargs['stride_w'] = strides[1]

            set_padding(config, layer.input_shape, kwargs)
            kwargs['group'] = layer.input_shape[3]
            kwargs['bias_term'] = False
            caffe_net[name] = L.Convolution(caffe_net[outputs[bottom]], **kwargs)
            blob = np.array(blobs[0]).transpose(2, 3, 0, 1)
            blob.shape = (1,) + blob.shape
            net_params[name] = blob

            name2 = name + '_'
            kwargs = {'num_output': config['filters'], 'kernel_size': 1, 'bias_term': config['use_bias']}
            caffe_net[name2] = L.Convolution(caffe_net[name], **kwargs)

            if config['use_bias'] == True:
                blob2 = []
                blob2.append(np.array(blobs[1]).transpose(3, 2, 0, 1))
                blob2.append(np.array(blobs[2]))
                blob2[0].shape = (1,) + blob2[0].shape
            else:
                blob2 = np.array(blobs[1]).transpose(3, 2, 0, 1)
                blob2.shape = (1,) + blob2.shape

            net_params[name2] = blob2
            name = name2

        elif layer_type == 'BatchNormalization':
            param = dict()
            variance = np.array(blobs[-1])
            mean = np.array(blobs[-2])

            if config['scale']:
                gamma = np.array(blobs[0])
                # sparam=[dict(lr_mult=0), dict(lr_mult=1)]
            else:
                gamma = np.ones(mean.shape, dtype=np.float32)
                # sparam=[dict(lr_mult=0, decay_mult=0), dict(lr_mult=1, decay_mult=1)]
                # sparam=[dict(lr_mult=0), dict(lr_mult=1)]
                sparam=[dict(lr_mult=0), dict(lr_mult=0)]
            
            if config['center']:
                beta = np.array(blobs[1])
                param['bias_term']=True
            else:
                beta = np.zeros(mean.shape, dtype=np.float32)
                param['bias_term']=False
            
            # caffe_net[name] = L.BatchNorm(caffe_net[outputs[bottom]], in_place=True)
            caffe_net[name] = L.BatchNorm(caffe_net[outputs[bottom]],  moving_average_fraction=layer.momentum, eps=layer.epsilon)
            net_params[name] = (mean, variance, np.array(1.0)) 
            name_s = name + 's'
            caffe_net[name_s] = L.Scale(caffe_net[name], in_place=True, scale_param=param)
            net_params[name_s] = (gamma, beta)
        elif layer_type == 'Dense':
            caffe_net[name] = L.InnerProduct(caffe_net[outputs[bottom]], 
            	num_output=config['units'], weight_filler=dict(type='xavier'))
            if config['use_bias']:
                weight=np.array(blobs[0]).transpose(1, 0)
                if type(layer._inbound_nodes[0].inbound_layers[0]).__name__ == 'Flatten':
                    flatten_shape=layer._inbound_nodes[0].inbound_layers[0].input_shape
                    for i in range(weight.shape[0]):
                        weight[i]=np.array(weight[i].reshape(flatten_shape[1],flatten_shape[2],flatten_shape[3]).transpose(2,0,1).reshape(weight.shape[1]))
                net_params[name] = (weight, np.array(blobs[1]))
            else:
                net_params[name] = (blobs[0])
                
            name_s = name + 's'
            if config['activation'] == 'softmax':
                caffe_net[name_s] = L.Softmax(caffe_net[name], in_place=True)
            elif config['activation'] == 'relu':
                caffe_net[name_s] = L.ReLU(caffe_net[name], in_place=True)
            elif config['activation'] == 'sigmoid':
                caffe_net[name_s] = L.Sigmoid(caffe_net[name], in_place=True)
        elif layer_type == 'Activation':
            if config['activation'] == 'relu':
                # caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]], in_place=True)
                if len(layer.input.consumers()) > 1:
                    caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]])
                else:
                    caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]], in_place=True)
            elif config['activation'] == 'sigmoid':
                caffe_net[name] = L.Sigmoid(caffe_net[outputs[bottom]], in_place=True)
            elif config['activation'] == 'LeakyReLU':
                # caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]], in_place=True)
                if len(layer.input.consumers()) > 1:
                    caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]],negative_slope=round(0.1,1))
                else:
                    caffe_net[name_s] = L.ReLU(caffe_net[outputs[bottom]], in_place=True,negative_slope=round(0.1,1))
            elif config['activation'] == 'relu6':
                #TODO
                caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]])
            elif config['activation']=='softmax':
                caffe_net[name] = L.Softmax(caffe_net[outputs[bottom]], in_place=True)
            else:
                raise Exception('Unsupported activation '+config['activation'])
        elif layer_type == 'Cropping2D':
            shape = layer.output_shape
            ddata = L.DummyData(shape=dict(dim=[1, shape[3],shape[1], shape[2]]))
            layers = []
            layers.append(caffe_net[outputs[bottom]])   
            layers.append(ddata)  # TODO
            caffe_net[name] = L.Crop(*layers)
        elif layer_type == 'Concatenate' or layer_type == 'Merge':
            layers = []
            for i in layer.input:
                layers.append(caffe_net[outputs[i.name]])
            caffe_net[name] = L.Concat(*layers, axis=1)
        elif layer_type == 'Add':
            layers = []
            for i in layer.input:
                layers.append(caffe_net[outputs[i.name]])
            caffe_net[name] = L.Eltwise(*layers, eltwise_param=dict(operation=P.Eltwise.SUM))
        elif layer_type == 'Multiply':
            layers = []
            for i in layer.input:
                layers.append(caffe_net[outputs[i.name]])
            caffe_net[name] = L.Eltwise(*layers, eltwise_param=dict(operation=P.Eltwise.PROD))
        elif layer_type == 'Flatten':
            caffe_net[name] = L.Flatten(caffe_net[outputs[bottom]])
        elif layer_type == 'Reshape':
            shape = config['target_shape']
            if len(shape) == 3:
                # shape = (layer.input_shape[0], shape[2], shape[0], shape[1])
                shape = (1, shape[2], shape[0], shape[1])
            elif len(shape) == 1:
                # shape = (layer.input_shape[0], 1, 1, shape[0])
                shape = (1, 1, 1, shape[0])
            caffe_net[name] = L.Reshape(caffe_net[outputs[bottom]], reshape_param={'shape':{'dim': list(shape)}})
        elif layer_type == 'MaxPooling2D' or layer_type == 'AvgPooling2D' or layer_type == 'AveragePooling2D':
            kwargs = {}
            if layer_type == 'MaxPooling2D':
                kwargs['pool'] = P.Pooling.MAX
            else:
                kwargs['pool'] = P.Pooling.AVE
                
            pool_size = config['pool_size']
            strides  = config['strides']
            
            if pool_size[0]!=pool_size[1]:
                raise Exception('Unsupported pool_size')
                    
            if strides[0]!=strides[1]:
                raise Exception('Unsupported strides')
            
            set_padding(config, layer.input_shape, kwargs)
            caffe_net[name] = L.Pooling(caffe_net[outputs[bottom]], kernel_size=pool_size[0], 
                stride=strides[0], **kwargs)
        elif layer_type == 'Dropout':
            # drop_ratio = config['rate']
            drop_ratio = 0.0
            caffe_net[name] = L.Dropout(caffe_net[outputs[bottom]], 
                dropout_param=dict(dropout_ratio=drop_ratio))
        elif layer_type == 'SpatialDropout2D':
            # drop_ratio = config['rate']
            drop_ratio = 0.0
            caffe_net[name] = L.Dropout(caffe_net[outputs[bottom]], 
                dropout_param=dict(dropout_ratio=drop_ratio))
        elif layer_type == 'GlobalAveragePooling2D':
            caffe_net[name] = L.Pooling(caffe_net[outputs[bottom]], pool=P.Pooling.AVE, 
                pooling_param=dict(global_pooling=True))
        elif layer_type == 'UpSampling2D':
            # print(factor)
            # upsample############
            # factor = config['size'][0]
            # kernel_size = 2 * factor - factor % 2
            # stride = factor
            # pad = int(math.ceil((factor - 1) / 2.0))
            # channels = layer.input_shape[-1]

            # caffe_net[name] = L.Deconvolution(caffe_net[outputs[bottom]], convolution_param=dict(num_output=channels, 
            #     group=channels, kernel_size=kernel_size, stride=stride, pad=pad, weight_filler=dict(type='bilinear'), 
            #     bias_term=False), param=dict(lr_mult=0, decay_mult=0))
            # net_params[name] = np.zeros((1,channels,1,4,4))

            ###############################
            interpolation = config['interpolation']
            weight_filler = dict(type='bilinear')
            if interpolation == 'nearest':
                weight_filler = dict(type='constant', value=1.0) 
            factor = config['size'][0]
            kernel_size = 2
            stride = 2
            pad = 0
            channels = layer.input_shape[-1]
           
            caffe_net[name] = L.Deconvolution(caffe_net[outputs[bottom]], convolution_param=dict(num_output=channels, 
                group=channels, kernel_size=kernel_size, stride=stride, pad=pad, weight_filler=weight_filler, 
                bias_term=False), param=dict(lr_mult=0, decay_mult=0))

            net_params[name] = np.ones((1,channels,1,2,2))
            ################################
            # deconvolution#########
            # stride = config['strides']
            # kernel_size = config['kernel_size']

            # use_bias = config['use_bias']
            # param = dict(bias_term=use_bias)
            # print(param)
            # ch = layer.input_shape[3]
            # caffe_net[name] = L.Deconvolution(caffe_net[outputs[bottom]], 
            #                           convolution_param=dict(num_output=ch, kernel=kernel_size,
            #                           stride=stride, pad_h=padding[0], pad_w=padding[1],bias_term=use_bias))
            # blobs[0] = np.array(blobs[0]).transpose(3, 2, 0, 1)
            # net_params[name] = blobs
        elif layer_type == 'ReLU':
            caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]], in_place=True, negative_slope=0.0)
        elif layer_type == 'LeakyReLU':
            caffe_net[name] = L.ReLU(caffe_net[outputs[bottom]], in_place=True, negative_slope=round(0.1,1))
        elif layer_type == 'ZeroPadding2D':
            padding = config['padding']
            print(padding)
            ch = layer.input_shape[3]
            caffe_net[name] = L.Convolution(caffe_net[outputs[bottom]], num_output=ch, kernel_size=1, stride=1,group = ch, 
                # pad_h=padding[0][0], pad_w=padding[1][0], convolution_param=dict(bias_term = False))
                pad_h=1, pad_w=1, convolution_param=dict(bias_term = False))
            net_params[name] = np.ones((1,ch,1,1,1))
        else:
            raise Exception('Unsupported layer type: '+layer_type)
        outputs[top]=name
    print(caffe_net)
    # replace empty layer with input blob
    net_proto = input_str + '\n' + 'layer {' + 'layer {'.join(str(caffe_net.to_proto()).split('layer {')[2:])

    with open(caffe_net_file, 'w') as f:
        f.write(net_proto)
    caffe_model = caffe.Net(caffe_net_file, caffe.TEST)
    for layer in caffe_model.params.keys():
        # if 'up_sampling2d' in layer:
        #    continue
        for n in range(0, len(caffe_model.params[layer])):
            caffe_model.params[layer][n].data[...] = net_params[layer][n]
    caffe_model.save(caffe_params_file)


if __name__ == '__main__':
    model = tf.keras.models.load_model('model.h5', compile=False)
    convert(model, 'model.prototxt', 'model.caffemodel')
