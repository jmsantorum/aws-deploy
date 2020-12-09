import click

from aws_deploy.ecs.cli import ecs_cli, get_ecs_client, wait_for_finish
from aws_deploy.ecs.helper import ScaleAction, EcsError


@ecs_cli.command()
@click.argument('cluster')
@click.argument('service')
@click.argument('desired_count', type=int)
@click.option('--ignore-warnings', is_flag=True,
              help='Do not fail deployment on warnings (port already in use or insufficient memory/CPU)')
@click.option('--timeout', default=300, type=int, show_default=True,
              help='Amount of seconds to wait for deployment before command fails. '
                   'To disable timeout (fire and forget) set to -1.')
@click.option('--sleep-time', default=1, type=int, show_default=True,
              help='Amount of seconds to wait between each check of the service.')
@click.pass_context
def scale(ctx, cluster, service, desired_count, ignore_warnings, timeout, sleep_time):
    """
    Scale a service up or down.

    \b
    CLUSTER is the name of your cluster (e.g. 'my-cluster') within ECS.
    SERVICE is the name of your service (e.g. 'my-app') within ECS.
    DESIRED_COUNT is the number of tasks your service should run.
    """

    try:
        click.secho(f'Scale [cluster={cluster}, service={service}, desired_count={desired_count}]')

        ecs_client = get_ecs_client(ctx)
        scale_action = ScaleAction(ecs_client, cluster, service)

        scale_action.scale(desired_count)

        click.secho(f'Successfully updated desired count to: {desired_count}', fg='green')

        wait_for_finish(
            action=scale_action,
            timeout=timeout,
            title='Scaling service',
            success_message='Scaling successful',
            failure_message='Scaling failed',
            ignore_warnings=ignore_warnings,
            sleep_time=sleep_time
        )
    except EcsError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
