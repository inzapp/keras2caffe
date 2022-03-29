import keras2caffe

from tensorflow.keras.models import load_model

if __name__ == '__main__':
    model = load_model('model.h5', compile=False)
    keras2caffe.convert(model, 'model.prototxt', 'model.caffemodel')
    print('save success')

