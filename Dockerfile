FROM ubuntu:20.04

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3 python3-pip

RUN pip3 install pytest==8.0.0 \
                 xmltodict==0.13.0 \
                 requests==2.31.0 \
                 Flask==3.0.2 \
                 geopy==2.4.1 \
                 astropy==5.2.2

WORKDIR /code

COPY iss_tracker.py .
COPY /test/test_iss_tracker.py .

ENTRYPOINT ["python3"]
CMD ["iss_tracker.py"]