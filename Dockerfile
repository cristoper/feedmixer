FROM bitnami/minideb:stretch

RUN install_packages python3-pip git
RUN pip3 install pipenv
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PIPENV_VENV_IN_PROJECT yes
COPY Pipfile Pipfile.lock feedmixer_api.py feedmixer_wsgi.py feedmixer.py /app/
WORKDIR /app/

RUN pipenv --three sync
RUN pipenv run pip3 install gunicorn
RUN chown nobody /app/
USER nobody

ENTRYPOINT ["pipenv", "run", "gunicorn"]
CMD ["-b", ":8000", "feedmixer_wsgi"]
