import click

from aws_deploy.ecs.cli import ecs_cli, get_ecs_client, print_diff
from aws_deploy.ecs.helper import LAUNCH_TYPE_EC2, LAUNCH_TYPE_FARGATE, RunAction, EcsError


@ecs_cli.command()
@click.argument('cluster')
@click.argument('task')
@click.argument('count', required=False, default=1)
@click.option('-c', '--command', type=(str, str), multiple=True,
              help='Overwrites the command in a container: <container> <command>')
@click.option('-e', '--env', type=(str, str, str), multiple=True,
              help='Adds or changes an environment variable: <container> <name> <value>')
@click.option('--env-file', type=(str, str), default=((None, None),), multiple=True, required=False,
              help='Load environment variables from .env-file')
@click.option('-s', '--secret', type=(str, str, str), multiple=True,
              help='Adds or changes a secret environment variable from the AWS Parameter Store '
                   '(Not available for Fargate): <container> <name> <parameter name>')
@click.option('--exclusive-env', is_flag=True, default=False, show_default=True,
              help='Set the given environment variables exclusively and remove all other pre-existing env variables '
                   'from all containers')
@click.option('--exclusive-secrets', is_flag=True, default=False, show_default=True,
              help='Set the given secrets exclusively and remove all other pre-existing secrets from all containers')
@click.option('--launch-type', type=click.Choice([LAUNCH_TYPE_EC2, LAUNCH_TYPE_FARGATE]), default=LAUNCH_TYPE_EC2,
              show_default=True, help='ECS Launch type.')
@click.option('--subnet', type=str, multiple=True,
              help='A subnet ID to launch the task within. Required for launch type FARGATE (multiple values possible)')
@click.option('--security-group', type=str, multiple=True,
              help='A security group ID to launch the task within. Required for launch type FARGATE '
                   '(multiple values possible)')
@click.option('--public-ip', is_flag=True, default=False, show_default=True,
              help='Should a public IP address be assigned to the task.')
@click.option('--platform-version', required=False,
              help='The version of the Fargate platform on which to run the task. Optional, FARGATE launch type only.')
@click.option('--diff/--no-diff', default=True, show_default=True,
              help='Print which values were changed in the task definition')
@click.pass_context
def run(ctx, cluster, task, count, command, env, env_file, secret, exclusive_env, exclusive_secrets, launch_type,
        subnet, security_group, public_ip, platform_version, diff):
    """
    Run a one-off task.

    \b
    CLUSTER is the name of your cluster (e.g. 'my-custer') within ECS.
    TASK is the name of your task definition (e.g. 'my-task') within ECS.
    COUNT is the number of tasks your service should run.
    """

    try:
        click.secho(f'Run task [cluster={cluster}, task={task}]')

        ecs_client = get_ecs_client(ctx)
        run_action = RunAction(ecs_client, cluster)

        td = run_action.get_task_definition(task)
        td.set_commands(**{key: value for (key, value) in command})
        td.set_environment(env, exclusive_env, env_file)
        td.set_secrets(secret, exclusive_secrets)

        if diff:
            print_diff(td, f'Using task definition: {task}')

        run_action.run(td, count, 'ECS Deploy', launch_type, subnet, security_group, public_ip, platform_version)

        click.secho(
            f'Successfully started {len(run_action.started_tasks)} instances of task: {td.family_revision}', fg='green'
        )

        for started_task in run_action.started_tasks:
            click.secho(f"- {started_task['taskArn']}", fg='green')
        click.secho(' ')
    except EcsError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
