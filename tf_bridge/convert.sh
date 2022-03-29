python3 main.py -sf tf -iw model.h5 -df caffe -om model --inNodeName=x --dstNodeName=Identity
cp -af main.py main.py.bak
rm -rf __pycache__
rm *.pb *.npy *.json *.py
mv main.py.bak main.py
