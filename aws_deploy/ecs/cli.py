from datetime import datetime, timedelta
from time import sleep

import click

from aws_deploy.notification.slack import SlackNotification
from .helper import EcsClient, TaskPlacementError
from ..notification.notification import Notification


def get_ecs_client(ctx) -> EcsClient:
    return EcsClient(
        aws_access_key_id=ctx.obj['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=ctx.obj['AWS_SECRET_ACCESS_KEY'],
        aws_session_token=ctx.obj['AWS_SESSION_TOKEN'],
        region_name=ctx.obj['AWS_REGION'],
        profile_name=ctx.obj['AWS_PROFILE']
    )


def get_notification(ctx) -> Notification:
    notification = SlackNotification(
        ctx.obj['SLACK_URL'],
        ctx.obj['SLACK_SERVICE_MATCH'],
        ctx.obj['SLACK_USERNAME']
    )

    return notification


@click.group(name='ecs')
@click.option('--aws-access-key-id', envvar='AWS_ACCESS_KEY_ID', required=False, help='AWS access key id')
@click.option('--aws-secret-access-key', envvar='AWS_SECRET_ACCESS_KEY', required=False, help='AWS secret access key')
@click.option('--aws-session-token', envvar='AWS_SESSION_TOKEN', required=False, help='AWS session token')
@click.option('--aws-region', envvar='AWS_REGION', required=False, help='AWS region (e.g. eu-west-1)')
@click.option('--aws-profile', envvar='AWS_PROFILE', required=False, help='AWS configuration profile name')
@click.option('--slack-url', required=False, envvar='SLACK_URL', help='Webhook URL of the Slack integration.')
@click.option('--slack-service-match', default='.*', required=False, envvar='SLACK_SERVICE_MATCH',
              help='A regular expression for defining, which services should be notified. (default: .* =all).')
@click.option('--slack-username', required=False, envvar='SLACK_USERNAME', default='ECS Deploy', help='Slack username.')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def ecs_cli(ctx, aws_access_key_id, aws_secret_access_key, aws_session_token, aws_region, aws_profile, slack_url,
            slack_service_match, slack_username, debug):
    ctx.ensure_object(dict)

    ctx.obj['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    ctx.obj['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    ctx.obj['AWS_SESSION_TOKEN'] = aws_session_token
    ctx.obj['AWS_REGION'] = aws_region
    ctx.obj['AWS_PROFILE'] = aws_profile

    ctx.obj['SLACK_URL'] = slack_url
    ctx.obj['SLACK_SERVICE_MATCH'] = slack_service_match
    ctx.obj['SLACK_USERNAME'] = slack_username

    ctx.obj['DEBUG'] = debug


def wait_for_finish(action, timeout, title, success_message, failure_message, ignore_warnings, sleep_time=1):
    click.secho(title, nl=False)
    waiting_timeout = datetime.now() + timedelta(seconds=timeout)
    service = action.get_service()
    inspected_until = None

    if timeout == -1:
        waiting = False
    else:
        waiting = True

    while waiting and datetime.now() < waiting_timeout:
        click.secho('.', nl=False)
        service = action.get_service()
        inspected_until = inspect_errors(
            service=service,
            failure_message=failure_message,
            ignore_warnings=ignore_warnings,
            since=inspected_until,
            timeout=False
        )
        waiting = not action.is_deployed(service)

        if waiting:
            sleep(sleep_time)

    inspect_errors(
        service=service,
        failure_message=failure_message,
        ignore_warnings=ignore_warnings,
        since=inspected_until,
        timeout=waiting
    )

    click.secho(f'\n{success_message}', fg='green')


def deploy_task_definition(deployment, task_definition, title, success_message, failure_message, timeout, deregister,
                           previous_task_definition, ignore_warnings, sleep_time):
    click.secho('Updating service')

    deployment.deploy(task_definition)

    click.secho(
        f'Successfully changed task definition to: {task_definition.family}:{task_definition.revision}', fg='green'
    )

    wait_for_finish(
        action=deployment,
        timeout=timeout,
        title=title,
        success_message=success_message,
        failure_message=failure_message,
        ignore_warnings=ignore_warnings,
        sleep_time=sleep_time
    )

    if deregister:
        deregister_task_definition(deployment, previous_task_definition)


def get_task_definition(action, task):
    if task:
        task_definition = action.get_task_definition(task)
    else:
        task_definition = action.get_current_task_definition(action.service)

    return task_definition


def create_task_definition(action, task_definition):
    click.secho('Creating new task definition revision')

    new_task_definition = action.update_task_definition(task_definition)

    click.secho(f'Successfully created revision: {new_task_definition.revision}', fg='green')

    return new_task_definition


def deregister_task_definition(action, task_definition):
    click.secho('Deregister task definition revision')

    action.deregister_task_definition(task_definition)

    click.secho(f'Successfully deregistered revision: {task_definition.revision}', fg='green')


def rollback_task_definition(deployment, old_td, new_td, timeout=600, sleep_time=1):
    click.secho(f'Rolling back to task definition: {old_td.family_revision}', fg='yellow')

    deploy_task_definition(
        deployment=deployment,
        task_definition=old_td,
        title='Deploying previous task definition',
        success_message='Rollback successful',
        failure_message='Rollback failed. Please check ECS Console',
        timeout=timeout,
        deregister=True,
        previous_task_definition=new_td,
        ignore_warnings=False,
        sleep_time=sleep_time
    )

    click.secho(
        f'Deployment failed, but service has been rolled back to previous task definition: {old_td.family_revision}',
        fg='yellow', err=True
    )


def print_diff(task_definition, title='Updating task definition'):
    if task_definition.diff:
        click.secho(title)
        for diff in task_definition.diff:
            click.secho(str(diff), fg='blue')
        click.secho('')


def inspect_errors(service, failure_message, ignore_warnings, since, timeout):
    error = False
    last_error_timestamp = since

    warnings = service.get_warnings(since)
    for timestamp in warnings:
        message = warnings[timestamp]
        click.secho('')
        if ignore_warnings:
            last_error_timestamp = timestamp
            click.secho(f'{timestamp}\nWARNING: {message}', fg='yellow', err=False)
            click.secho('Continuing.', nl=False)
        else:
            click.secho(f'{timestamp}\nERROR: {message}', fg='red', err=True)
            error = True

    if service.older_errors:
        click.secho('')
        click.secho('Older errors', fg='yellow', err=True)
        for timestamp in service.older_errors:
            click.secho(f'{timestamp}\n{service.older_errors[timestamp]}', fg='yellow', err=True)

    if timeout:
        error = True
        failure_message += ' due to timeout. Please see: https://github.com/jmsantorum/aws-deploy#timeout'
        click.secho('')

    if error:
        raise TaskPlacementError(failure_message)

    return last_error_timestamp
