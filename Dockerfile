FROM bitnami/minideb@sha256:03d145bf50918df2acd08346c600b0688f8b16521b5ea462f6b503fe3a2f010d as install

RUN install_packages python3-pip git
RUN pip3 --no-cache-dir install pipenv
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PIPENV_VENV_IN_PROJECT yes
COPY Pipfile Pipfile.lock feedmixer_api.py feedmixer_wsgi.py feedmixer.py /app/

WORKDIR /app/
RUN pipenv sync && apt purge
RUN pipenv run pip3 install gunicorn

# build layer without git:
# (we still need pip because newer pipenv apparently depend on it)
FROM bitnami/minideb@sha256:03d145bf50918df2acd08346c600b0688f8b16521b5ea462f6b503fe3a2f010d
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PIPENV_VENV_IN_PROJECT yes

RUN install_packages python3-pip python3-distutils
copy --from=install /app/ /app
copy --from=install /usr/local/lib/python3.9/dist-packages/ /usr/local/lib/python3.9/dist-packages/
copy --from=install /usr/local/bin/pipenv /usr/local/bin/pipenv

RUN chown nobody /app/
WORKDIR /app/

USER nobody
ENTRYPOINT ["pipenv", "run", "gunicorn"]
CMD ["-b", ":8000", "feedmixer_wsgi"]
