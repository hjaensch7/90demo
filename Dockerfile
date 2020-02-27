FROM python:3

ADD test_component.py /
ADD v9.py /

ENTRYPOINT ["python","-u","./test_component.py"]
CMD []
