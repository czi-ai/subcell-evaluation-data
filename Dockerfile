FROM ubuntu:24.04
RUN apt update && apt-get install parallel python3-pip ffmpeg libsm6 libxext6 libpng16-16t64 -y
RUN pip3 install --break-system-packages tifffile 'numpy<2' opencv-python stardist scikit-image tensorflow awscli

# Place StarDist model file at expected Keras cache location; otherwise, the model loader tries to
# download it at runtime, which is a reliability issue running at scale.
ADD https://github.com/stardist/stardist-models/releases/download/v0.1/python_2D_versatile_fluo.zip /root/.keras/models/StarDist2D/2D_versatile_fluo/2D_versatile_fluo.zip

RUN mkdir /SubCell
COPY convert_allencell.py convert_opencell_stardist.py /SubCell/
