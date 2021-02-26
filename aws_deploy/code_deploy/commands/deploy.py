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
@click.option('--module-version', type=str, help='Module version to be deployed')
@click.option('--tag-only', help='New tag to apply to ALL images defined in the task (multi-container task). If provided this will override value specified in image name argument.')  # noqa: E501
@click.option('--timeout', default=600, type=int, show_default=True, help='Amount of seconds to wait for deployment before command fails. To disable timeout (fire and forget) set to -1.')  # noqa: E501
@click.option('--sleep-time', default=1, type=int, show_default=True, help='Amount of seconds to wait between each check of the service.')  # noqa: E501
@click.option('--deregister/--no-deregister', default=False, show_default=True, help='Deregister or keep the old task definition.')  # noqa: E501
@click.option('--skip-latest-tag', is_flag=True, default=True, show_default=True, help='Skip images with latest tag.')  # noqa: E501
@click.option('--show-diff/--no-diff', default=True, show_default=True, help='Print which values were changed in the task definition')  # noqa: E501
@click.pass_context
def deploy(ctx, application_name, deployment_group_name, task_definition, module_version, tag_only, timeout, sleep_time,
           deregister, skip_latest_tag, show_diff):
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

        # fetch application
        click.secho(f'Fetching application [application_name={application_name}] -> ', nl=False)
        application = code_deploy_client.get_application(application_name=application_name)
        click.secho(f'{application.application_id}', fg='green')

        # fetch deployment group
        click.secho(f'Fetching deployment_group [deployment_group_name={deployment_group_name}] -> ', nl=False)
        deployment_group = code_deploy_client.get_deployment_group(
            application_name=application.application_name, deployment_group_name=deployment_group_name
        )
        click.secho(f'{deployment_group.deployment_group_id}', fg='green')

        # fetch application revision
        click.secho(f'Fetching application_revision [application_name={application_name}, deployment_group_name={deployment_group_name}] -> ', nl=False)  # noqa: E501
        application_revision = code_deploy_client.get_application_revision(
            application_name=application.application_name, deployment_group=deployment_group
        )
        if application_revision:
            click.secho(f'[RevisionType={application_revision.revision.revision_type}]', fg='green')
        else:
            click.secho('Not Found!', fg='red')

        # fetch task definition
        if application_revision:
            if task_definition:
                requested_task_definition_arn = task_definition
                current_task_definition_arn = application_revision.revision.get_task_definition()
            else:
                click.secho('Task definition not present, fetching it -> ', nl=False)
                requested_task_definition_arn = application_revision.revision.get_task_definition()
                current_task_definition_arn = application_revision.revision.get_task_definition()
                click.secho(f'{requested_task_definition_arn}', fg='green')
        else:
            if task_definition:
                requested_task_definition_arn = task_definition
                current_task_definition_arn = None
            else:
                click.secho('Task definition not present, fetching it -> ', nl=False)
                requested_ecs_service = code_deploy_client.get_service(deployment_group=deployment_group)
                current_task_definition_arn = requested_ecs_service.task_definition
                last_task_definition = code_deploy_client.get_task_definition(
                    task_definition_arn=current_task_definition_arn.rsplit(':', 1)[0]
                )
                requested_task_definition_arn = last_task_definition.arn
                click.secho(f'{requested_task_definition_arn}', fg='green')

        requested_task_definition = code_deploy_client.get_task_definition(
            task_definition_arn=requested_task_definition_arn
        )
        click.secho(f"Requested task definition: '{requested_task_definition.arn}'")

        # check module version
        if module_version:
            requested_module_version = module_version
        else:
            click.secho('ModuleVersion not present, fetching it -> ', nl=False)
            requested_module_version = requested_task_definition.get_tag('ModuleVersion')
            click.secho(f'{requested_module_version}', fg='green')

        # fetch compatible task definition
        if requested_module_version:
            click.secho(f"Requested ModuleVersion: '{requested_module_version}'")
            selected_task_definition = code_deploy_client.get_task_definition_filtered(
                family=requested_task_definition.family, module_version=requested_module_version
            )
        else:
            click.secho('ModuleVersion not present, skipping it')
            selected_task_definition = requested_task_definition

        # selected tag
        if tag_only:
            selected_tag = tag_only
        else:
            selected_tag = list(selected_task_definition.images)[0][1].rsplit(':', 1)[1]

        if skip_latest_tag:
            if 'latest' == selected_tag:
                current_task_definition = code_deploy_client.get_task_definition(
                    task_definition_arn=current_task_definition_arn
                )
                selected_tag = list(current_task_definition.images)[0][1].rsplit(':', 1)[1]

                if 'latest' == selected_tag:
                    raise CodeDeployError('Cannot find valid tag')

        selected_task_definition.set_images(tag=selected_tag)

        if selected_task_definition.updated:
            selected_task_definition.set_tag('Terraform', 'false')
            selected_task_definition.show_diff(show_diff=show_diff)

            click.secho('Creating new task definition revision -> ', nl=False)
            new_task_definition = code_deploy_client.register_task_definition(task_definition=selected_task_definition)
            click.secho(f'{new_task_definition.revision}', fg='green')
        else:
            click.secho('No changes required, task definition is up to date!', fg='green')
            new_task_definition = selected_task_definition

        if application_revision:
            application_revision.set_task_definition(new_task_definition=new_task_definition)

            if application_revision.updated:
                application_revision.show_diff(show_diff=show_diff)

            new_revision = application_revision.revision
        else:
            new_revision = code_deploy_client.create_new_revision(task_definition=new_task_definition)

        # Deployment
        click.secho('Deploying new application revision', nl=False)

        deployment = code_deploy_client.create_deployment(
            application_name=application_name,
            deployment_group_name=deployment_group_name,
            revision=new_revision
        )

        wait_for_finish(
            lambda: code_deploy_client.get_deployment(deployment_id=deployment.deployment_id),
            timeout=timeout,
            sleep_time=sleep_time
        )

        # TODO define which task we want to deregister
        # if deregister and task_definition.updated:
        #     click.secho(f'Deregister task definition revision: {task_definition.revision}')
        #
        #     code_deploy_client.deregister_task_definition(task_definition.arn)
        #
        #     click.secho(f'Successfully deregistered revision: {task_definition.revision}', fg='green')

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
