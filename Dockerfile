FROM bitnami/minideb:stretch

COPY requirements.txt /requirements.txt
RUN install_packages python3-pip python3-setuptools git
RUN pip3 install -r /requirements.txt
RUN pip3 install gunicorn

COPY feedmixer_api.py feedmixer_wsgi.py feedmixer.py /app/
WORKDIR /app/
RUN chown nobody /app/
USER nobody

ENTRYPOINT ["gunicorn"]
CMD ["-b", ":8000", "feedmixer_wsgi"]
