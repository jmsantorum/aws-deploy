import json

import click

from aws_deploy.ecs.cli import ecs_cli, get_ecs_client
from aws_deploy.ecs.helper import DiffAction, EcsError


@ecs_cli.command()
@click.argument('task')
@click.argument('revision_a')
@click.argument('revision_b')
@click.pass_context
def diff(ctx, task, revision_a, revision_b):
    """
    Compare two task definition revisions.

    \b
    TASK is the name of your task definition (e.g. 'my-task') within ECS.
    COUNT is the number of tasks your service should run.
    """

    try:
        ecs_client = get_ecs_client(ctx)
        action = DiffAction(ecs_client)

        td_a = action.get_task_definition(f'{task}:{revision_a}')
        td_b = action.get_task_definition(f'{task}:{revision_b}')

        result = td_a.diff_raw(td_b)
        for difference in result:
            if difference[0] == 'add':
                click.secho(f'{difference[0]}: {difference[1]}', fg='green')
                for added in difference[2]:
                    click.secho(f'    + {added[0]}: {json.dumps(added[1])}', fg='green')

            if difference[0] == 'change':
                click.secho(f'{difference[0]}: {difference[1]}', fg='yellow')
                click.secho(f'    - {json.dumps(difference[2][0])}', fg='red')
                click.secho(f'    + {json.dumps(difference[2][1])}', fg='green')

            if difference[0] == 'remove':
                click.secho(f'{difference[0]}: {difference[1]}', fg='red')
                for removed in difference[2]:
                    click.secho(f'    - {removed[0]}: {removed[1]}', fg='red')
    except EcsError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
