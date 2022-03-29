## keras2caffe

1. create virtual environment<br>
    ```
    python3 -m venv ~/venv
    source ~/venv/bin/activate
    ```

2. install tensorflow and scikit_image<br>
    ```
    python3 -m pip install --upgrade pip
    python3 -m pip install tensorflow-cpu==2.3.1
    python3 -m pip install scikit-image==0.17.2
    ```

3. locate keras model.h5 to here and run command<br>
    ```
    ./convert.sh
    ```
