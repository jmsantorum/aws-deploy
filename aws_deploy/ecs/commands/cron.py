import click

from aws_deploy.ecs.cli import ecs_cli, get_ecs_client, print_diff, create_task_definition, deregister_task_definition
from aws_deploy.ecs.helper import RunAction, EcsError


@ecs_cli.command()
@click.argument('cluster')
@click.argument('task')
@click.argument('rule')
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
              help='Set the given environment variables exclusively and remove all other '
                   'pre-existing env variables from all containers')
@click.option('--exclusive-secrets', is_flag=True, default=False, show_default=True,
              help='Set the given secrets exclusively and remove all other pre-existing secrets from all containers')
@click.option('-r', '--role', type=str, help='Sets the task\'s role ARN: <task role ARN>')
@click.option('--deregister/--no-deregister', default=True, show_default=True,
              help='Deregister or keep the old task definition.')
@click.option('--diff/--no-diff', default=True, show_default=True,
              help='Print which values were changed in the task definition')
@click.pass_context
def cron(ctx, cluster, task, rule, image, tag, command, env, env_file, secret, exclusive_env, exclusive_secrets, role,
         deregister, diff):
    """
    Update a scheduled task.

    \b
    CLUSTER is the name of your cluster (e.g. 'my-cluster') within ECS.
    TASK is the name of your task definition (e.g. 'my-task') within ECS.
    RULE is the name of the rule to use the new task definition.
    """

    try:
        click.secho(f'Update task definition [cluster={cluster}, task={task}, rule={rule}]')

        ecs_client = get_ecs_client(ctx)
        action = RunAction(ecs_client, cluster)

        td = action.get_task_definition(task)
        td.set_images(tag, **{key: value for (key, value) in image})
        td.set_commands(**{key: value for (key, value) in command})
        td.set_environment(env, exclusive_env, env_file)
        td.set_secrets(secret, exclusive_secrets)
        td.set_role_arn(role)

        if diff:
            print_diff(td)

        new_td = create_task_definition(action, td)

        click.secho('Updating scheduled task')

        ecs_client.update_rule(cluster=cluster, rule=rule, task_definition=new_td)

        click.secho(f'Successfully updated scheduled task {rule}', fg='green')

        if deregister:
            deregister_task_definition(action, td)
    except EcsError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
