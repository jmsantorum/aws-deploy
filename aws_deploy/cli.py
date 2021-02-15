import sys

import click

from aws_deploy import VERSION
from aws_deploy.code_deploy.cli import code_deploy_cli
from aws_deploy.ecs.cli import ecs_cli
from aws_deploy.batch.cli import batch_cli


@click.group(context_settings={'terminal_width': 120})
@click.version_option(version=VERSION, prog_name='aws-deploy')
def cli():  # pragma: no cover
    pass


cli.add_command(ecs_cli)
cli.add_command(code_deploy_cli)
cli.add_command(batch_cli)

if __name__ == '__main__':  # pragma: no cover
    try:
        cli(obj={})
    except Exception as e:
        click.secho(str(e), fg='red', err=True)
        sys.exit(1)
