import click

from aws_deploy.batch.cli import batch_cli, get_batch_client
from aws_deploy.batch.helper import BatchError


@batch_cli.command()
@click.argument('job-definition-name')
@click.option('--tag',  help='New tag to apply to the image defined in the job definition')
@click.option('--deregister/--no-deregister', default=False, show_default=True, help='Deregister or keep the old task definition.')  # noqa: E501
@click.option('--skip-latest-tag', is_flag=True, default=True, show_default=True, help='Skip images with latest tag.')
@click.option('--show-diff/--no-diff', default=True, show_default=True, help='Print which values were changed in the task definition')  # noqa: E501
@click.pass_context
def deploy(ctx, job_definition_name, tag, deregister, skip_latest_tag, show_diff):
    """
    Deploys a job definition revision.

    \b
    JOB_DEFINITION_NAME is the name of an AWS Batch Job definition.
    """

    try:
        click.secho(f'Deploy [job_definition_name={job_definition_name}]')
        batch_client = get_batch_client(ctx)

        # retrieve last active job definition revision
        click.secho(f'Fetching job definition [job_definition_name={job_definition_name}] -> ', nl=False)
        selected_job_definition = batch_client.get_job_definition(job_definition_name=job_definition_name)
        click.secho(f'{selected_job_definition.arn}')

        # update selected job definition
        selected_container_properties = selected_job_definition.container_properties
        if tag:
            selected_container_properties.set_image(tag=tag)
        selected_job_definition.set_tag('Terraform', 'false')

        if skip_latest_tag:
            image_tag = selected_container_properties.image.rsplit(':', 1)[1]
            if image_tag == 'latest':
                last_job_definition = batch_client.get_last_job_definition(
                    job_definition_name=job_definition_name
                )

                if last_job_definition:
                    last_image = last_job_definition.container_properties.image
                    last_tag = last_image.rsplit(':', 1)[1]
                    click.secho(f'Last tag is "{last_tag}"')

                    if last_tag != 'latest':
                        click.secho(f'Replace "latest" tag with "{last_tag}"')
                        selected_container_properties.set_image(image=last_image)
                    else:
                        raise BatchError('Cannot replace "latest" tag')
                else:
                    raise BatchError('Cannot replace "latest" tag')

        if selected_job_definition.updated:
            selected_job_definition.show_diff(show_diff=show_diff)

            click.secho('Creating new job definition revision')

            new_job_definition = batch_client.register_job_definition(job_definition=selected_job_definition)

            click.secho(f'Successfully created new job definition revision: {new_job_definition.revision}', fg='green')
        else:
            click.secho('No changes required, job definition is up to date!')

        # TODO define which job we want to deregister
        # if deregister:
        #     click.secho(f'Deregister job definition revision: {job_definition.revision}')
        #
        #     batch_client.deregister_job_definition(job_definition.arn)
        #
        #     click.secho(f'Successfully deregistered revision: {job_definition.revision}', fg='green')

    except BatchError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
