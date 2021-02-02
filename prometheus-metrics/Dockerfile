FROM python:3.8-alpine

ADD main.py /
ADD settings.py /
ADD requirements.txt /

RUN pip install -r requirements.txt

CMD ["python", "-u", "./main.py"]