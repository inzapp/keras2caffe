## keras2caffe

Keras h5 model to caffemodel, prototxt converter

Two versions are available for model conversion

tf_bridge : convert keras h5 model to tensorflow model, and convert tensorflow model to caffemodel with prototxt using built in mmdnn

keras_direct : convert keras h5 model to caffemodel with prototxt directly with custom converter using built in caffe

1. create virtual environment<br>
    ```
    $ python3 -m venv ~/venv
    $ source ~/venv/bin/activate
    ```

2. install tensorflow and scikit_image<br>
    ```
    $ python3 -m pip install --upgrade pip
    $ python3 -m pip install tensorflow-cpu==2.3.1
    $ python3 -m pip install scikit-image==0.17.2
    ```

3. locate keras model.h5 to here and run command<br>
    ```
    # tf_bridge
    $ cd ./keras2caffe/tf_bridge/
    $ mv your_model.h5 model.h5
    $ ./convert.sh
    
    # keras_direct
    $ cd ./keras2caffe/keras_direct/
    $ mv your_model.h5 model.h5
    $ python3 convert.py
    ```
