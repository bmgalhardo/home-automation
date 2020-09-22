FROM python:3.8-alpine

ADD cam-control.py /
ADD requirements.txt /
RUN pip install -r requirements.txt

CMD ["python", "./cam-control.py"]