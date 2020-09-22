FROM python:3.8.1-slim

RUN apt-get update
RUN apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev

RUN mkdir /videos

ADD cam-record.py /
ADD requirements.txt /
RUN pip install -r requirements.txt

CMD ["python", "./cam-record.py"]