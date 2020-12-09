import click

from aws_deploy.code_deploy.helper import CodeDeployClient
from aws_deploy.notification.notification import Notification
from aws_deploy.notification.slack import SlackNotification


def get_code_deploy_client(ctx) -> CodeDeployClient:
    return CodeDeployClient(
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


@click.group(name='code-deploy')
@click.option('--aws-access-key-id', envvar='AWS_ACCESS_KEY_ID', required=False, help='AWS access key id')
@click.option('--aws-secret-access-key', envvar='AWS_SECRET_ACCESS_KEY', required=False, help='AWS secret access key')
@click.option('--aws-session-token', envvar='AWS_SESSION_TOKEN', required=False, help='AWS session token')
@click.option('--aws-region', envvar='AWS_REGION', required=False, help='AWS region (e.g. eu-west-1)')
@click.option('--aws-profile', envvar='AWS_PROFILE', required=False, help='AWS configuration profile name')
@click.option('-v', '--verbose', default=False)
@click.pass_context
def code_deploy_cli(ctx, aws_access_key_id, aws_secret_access_key, aws_session_token, aws_region, aws_profile, verbose):
    ctx.ensure_object(dict)

    ctx.obj['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    ctx.obj['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    ctx.obj['AWS_SESSION_TOKEN'] = aws_session_token
    ctx.obj['AWS_REGION'] = aws_region
    ctx.obj['AWS_PROFILE'] = aws_profile

    ctx.obj['VERBOSE'] = verbose
