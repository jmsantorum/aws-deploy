import click

from aws_deploy.ecs.cli import (
    ecs_cli, get_ecs_client, get_task_definition, print_diff, create_task_definition, deploy_task_definition,
    rollback_task_definition
)
from aws_deploy.ecs.helper import DeployAction, TaskPlacementError, EcsError


@ecs_cli.command()
@click.argument('cluster')
@click.argument('service')
@click.option('--task', type=str,
              help='Task definition to be deployed. Can be a task ARN or a task family with optional revision')
@click.option('-i', '--image', type=(str, str), multiple=True,
              help='Overwrites the image for a container: <container> <image>')
@click.option('-t', '--tag', help='Changes the tag for ALL container images')
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
@click.option('-r', '--role', type=str, help='Sets the task\'s role ARN: <task role ARN>')
@click.option('-x', '--execution-role', type=str, help='Sets the execution\'s role ARN: <execution role ARN>')
@click.option('--ignore-warnings', is_flag=True,
              help='Do not fail deployment on warnings (port already in use or insufficient memory/CPU)')
@click.option('--timeout', default=300, type=int, show_default=True,
              help='Amount of seconds to wait for deployment before command fails. '
                   'To disable timeout (fire and forget) set to -1.')
@click.option('--sleep-time', default=1, type=int, show_default=True,
              help='Amount of seconds to wait between each check of the service.')
@click.option('--deregister/--no-deregister', default=True, show_default=True,
              help='Deregister or keep the old task definition.')
@click.option('--rollback/--no-rollback', default=False, show_default=True,
              help='Rollback to previous revision, if deployment failed.')
@click.option('--diff/--no-diff', default=True, show_default=True,
              help='Print which values were changed in the task definition')
@click.pass_context
def deploy(ctx, cluster, service, task, image, tag, command, env, env_file, secret, exclusive_env, exclusive_secrets,
           role, execution_role, ignore_warnings, timeout, sleep_time, deregister, rollback, diff):
    """
    Redeploy or modify a service.

    \b
    CLUSTER is the name of your cluster (e.g. 'my-cluster') within ECS.
    SERVICE is the name of your service (e.g. 'my-app') within ECS.

    When not giving any other options, the task definition will not be changed.
    It will just be duplicated, so that all container images will be pulled and redeployed.
    """

    try:
        click.secho(f'Deploy [cluster={cluster}, service={service}]')

        ecs_client = get_ecs_client(ctx)
        deploy_action = DeployAction(ecs_client, cluster, service)

        td = get_task_definition(deploy_action, task)
        td.set_images(tag, **{key: value for (key, value) in image})
        td.set_commands(**{key: value for (key, value) in command})
        td.set_environment(env, exclusive_env, env_file)
        td.set_secrets(secret, exclusive_secrets)
        td.set_role_arn(role)
        td.set_execution_role_arn(execution_role)

        if diff:
            print_diff(td)

        new_td = create_task_definition(deploy_action, td)

        try:
            deploy_task_definition(
                deployment=deploy_action,
                task_definition=new_td,
                title='Deploying new task definition',
                success_message='Deployment successful',
                failure_message='Deployment failed',
                timeout=timeout,
                deregister=deregister,
                previous_task_definition=td,
                ignore_warnings=ignore_warnings,
                sleep_time=sleep_time
            )
        except TaskPlacementError:
            if rollback:
                rollback_task_definition(deploy_action, td, new_td, sleep_time=sleep_time)

            raise
    except EcsError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
