FROM public.ecr.aws/lambda/python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . ${LAMBDA_TASK_ROOT}/package

RUN uv pip install ${LAMBDA_TASK_ROOT}/package --target ${LAMBDA_TASK_ROOT} --no-cache --system

ENV DUCKDB_EXTENSION_DIR=/opt/duckdb_extensions
RUN python -c "import duckdb; con = duckdb.connect(config={'extension_directory': '/opt/duckdb_extensions'}); con.install_extension('httpfs')"

CMD ["answer_checker.handler.lambda_handler"]
