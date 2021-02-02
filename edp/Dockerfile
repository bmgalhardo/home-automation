FROM python:3.8-alpine

ADD edp.py /
ADD app.py /
ADD requirements.txt /

RUN pip install -r requirements.txt

CMD ["flask", "run", "-h", "0.0.0.0"]