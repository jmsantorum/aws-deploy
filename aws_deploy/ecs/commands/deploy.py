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
@click.option('--module-version', type=str, help='Module version to be deployed')
@click.pass_context
def deploy(ctx, cluster, service, task, image, tag, command, env, env_file, secret, exclusive_env, exclusive_secrets,
           role, execution_role, ignore_warnings, timeout, sleep_time, deregister, rollback, diff, module_version):
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

        # fetch task definition
        requested_ecs_service = deploy_action.get_service()
        click.secho(f'Fetching task definition [service_name={requested_ecs_service.name}]-> ', nl=False)
        current_task_definition_arn = requested_ecs_service.task_definition

        last_task_definition = get_task_definition(deploy_action,
            task=current_task_definition_arn.rsplit(':', 1)[0]
        )
        requested_task_definition_arn = last_task_definition.arn
        click.secho(f'{requested_task_definition_arn}', fg='green')

        requested_task_definition = get_task_definition(deploy_action,
            task=requested_task_definition_arn
        )
        click.secho(f"Requested task definition: '{requested_task_definition.arn}'")

        # check module version
        if module_version:
            requested_module_version = module_version
        else:
            click.secho('ModuleVersion not present, fetching it -> ', nl=False)
            current_task_definition = get_task_definition(deploy_action,
                task=current_task_definition_arn
            )
            requested_module_version = current_task_definition.get_tag('ModuleVersion')
            click.secho(f'{requested_module_version}', fg='green')

        # fetch compatible task definition
        if requested_module_version:
            click.secho(f"Requested ModuleVersion: '{requested_module_version}'")
            selected_task_definition = ecs_client.get_task_definition_filtered(
                family=requested_task_definition.family, module_version=requested_module_version
            )
        else:
            click.secho('ModuleVersion not present, skipping it')
            selected_task_definition = requested_task_definition
        click.secho(f"Selected task definition: '{selected_task_definition.arn}'")

        # selected tag
        if tag and tag != 'null':
            selected_tag = tag
        else:
            selected_tag = list(selected_task_definition.images)[0][1].rsplit(':', 1)[1]

        # skip latest tag
        if 'latest' in selected_tag:
            current_task_definition = get_task_definition(deploy_action,
                task=current_task_definition_arn
            )
            selected_tag = list(current_task_definition.images)[0][1].rsplit(':', 1)[1]

            if 'latest' in selected_tag:
                raise EcsError('Cannot find valid tag')
        selected_task_definition.set_images(tag=selected_tag)

        if selected_task_definition.updated:
            selected_task_definition.set_tag('Terraform', 'false')
            selected_task_definition.set_tag('ImageTag', selected_tag)
            selected_task_definition.show_diff(show_diff=True)

            click.secho('Creating new task definition revision -> ', nl=False)
            new_task_definition = create_task_definition(deploy_action, task_definition=selected_task_definition)
            click.secho(f'{new_task_definition.revision}', fg='green')
        else:
            click.secho('No changes required, task definition is up to date!', fg='green')
            new_task_definition = selected_task_definition

        td = get_task_definition(deploy_action, new_task_definition.arn)
        # td.set_images(tag, **{key: value for (key, value) in image})
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
