from datetime import datetime, timedelta
from time import sleep
from typing import Callable

import click

from aws_deploy.code_deploy.cli import code_deploy_cli, get_code_deploy_client
from aws_deploy.code_deploy.helper import CodeDeployError, CodeDeployDeployment


@code_deploy_cli.command()
@click.argument('application-name')
@click.argument('deployment-group-name')
@click.option('--task-definition', type=str, help='Task definition to be deployed. Can be a task ARN or a task family with optional revision')  # noqa: E501
@click.option('--tag-only', help='New tag to apply to ALL images defined in the task (multi-container task). If provided this will override value specified in image name argument.')  # noqa: E501
@click.option('--timeout', default=300, type=int, show_default=True, help='Amount of seconds to wait for deployment before command fails. To disable timeout (fire and forget) set to -1.')  # noqa: E501
@click.option('--sleep-time', default=1, type=int, show_default=True, help='Amount of seconds to wait between each check of the service.')  # noqa: E501
@click.option('--deregister/--no-deregister', default=True, show_default=True, help='Deregister or keep the old task definition.')  # noqa: E501
@click.option('--show-diff/--no-diff', default=True, show_default=True, help='Print which values were changed in the task definition')  # noqa: E501
@click.pass_context
def deploy(ctx, application_name, deployment_group_name, task_definition, tag_only, timeout, sleep_time, deregister,
           show_diff):
    """
    Deploys an application revision through the specified deployment group.

    \b
    APPLICATION_NAME is the name of an AWS CodeDeploy application.
    DEPLOYMENT_GROUP_NAME is the name of the deployment group.

    When not giving any other options, the task definition will not be changed.
    It will just be duplicated, so that all container images will be pulled and redeployed.
    """

    try:
        click.secho(f'Deploy [application_name={application_name}, deployment_group_name={deployment_group_name}]')

        code_deploy_client = get_code_deploy_client(ctx)

        # retrieve current application revision
        application = code_deploy_client.get_application(application_name=application_name)
        deployment_group = code_deploy_client.get_deployment_group(
            application_name=application.application_name, deployment_group_name=deployment_group_name
        )
        application_revision = code_deploy_client.get_application_revision(
            application_name=application.application_name, deployment_group=deployment_group
        )

        # check task definition
        if task_definition:
            task_definition_arn = task_definition
        else:
            task_definition_arn = application_revision.revision.get_task_definition()

        task_definition = code_deploy_client.get_task_definition(task_definition_arn=task_definition_arn)

        # update task definition
        task_definition.set_images(tag=tag_only)

        if task_definition.updated:
            task_definition.show_diff(show_diff=show_diff)

            click.secho('Creating new task definition revision')

            new_task_definition = code_deploy_client.register_task_definition(task_definition)
            application_revision.set_task_definition(new_task_definition)

            click.secho(f'Successfully created new task definition revision: {new_task_definition.revision}', fg='green')  # noqa: E501

        # update application revision
        if application_revision.updated:
            application_revision.show_diff(show_diff=show_diff)

        # Deployment
        click.secho('Deploying new application revision', nl=False)

        deployment = code_deploy_client.create_deployment(
            application_name=application.application_name,
            deployment_group_name=deployment_group.deployment_group_name,
            revision=application_revision.revision
        )

        wait_for_finish(
            lambda: code_deploy_client.get_deployment(deployment_id=deployment.deployment_id),
            timeout=timeout,
            sleep_time=sleep_time
        )

        if deregister and task_definition.updated:
            click.secho(f'Deregister task definition revision: {task_definition.revision}')

            code_deploy_client.deregister_task_definition(task_definition.arn)

            click.secho(f'Successfully deregistered revision: {task_definition.revision}', fg='green')

    except CodeDeployError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)


def wait_for_finish(get_deployment: Callable[[], CodeDeployDeployment], timeout, sleep_time=1):
    waiting_timeout = datetime.now() + timedelta(seconds=timeout)
    deployment = get_deployment()

    if timeout > -1:
        while datetime.now() < waiting_timeout:
            if not deployment.is_waiting():
                break

            sleep(sleep_time)
            click.secho('.', nl=False)
            deployment = get_deployment()
    click.secho('')

    if deployment.is_success():
        click.secho('Deployment successful', fg='green')
    elif deployment.is_error():
        error_type = deployment.error_info['code']
        error_message = deployment.error_info['message']
        raise CodeDeployError(f'Deployment failed [type="{error_type}", reason="{error_message}"]')
    else:
        raise CodeDeployError('Deployment failed due to timeout')
