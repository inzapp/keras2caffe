## keras2caffe

1. create virtual environment<br>
    ```
    python3 -m venv ~/venv
    source ~/venv/bin/activate
    ```

2. move mmdnn package to virtual env module path<br>
    ```
    mv ./mmdnn ~/venv/lib/python3.6/site-package/
    ```

3. install caffe cpu<br>
    ```
    sudo apt install python3-caffe-cpu
    ```

4. link caffe to virtual env module path<br>
    ```
    ln -s /usr/lib/python3/dist-packages/caffe/ ~/venv/lib/python3.6/site-packages/caffe
    ```

5. install tensorflow and scikit_image<br>
    ```
    python3 -m pip install --upgrade pip
    python3 -m pip install tensorflow-cpu==2.3.1
    python3 -m pip install scikit-image==0.17.2
    ```

6. locate keras model.h5 to here and run command<br>
    ```
    ./convert.sh
    ```
