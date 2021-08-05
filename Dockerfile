FROM python:3.9-alpine AS base

RUN apk --no-cache --update add jq curl
RUN pip install awscli pipenv


FROM base AS production

WORKDIR /opt/aws-deploy

COPY Pipfile Pipfile.lock /opt/aws-deploy/
RUN pipenv install --system --deploy

COPY . /opt/aws-deploy
ENV PATH "$PATH:/opt/aws-deploy/bin"

CMD ["aws-deploy"]
