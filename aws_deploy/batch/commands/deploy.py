from distutils.util import strtobool

import click

from aws_deploy.batch.cli import batch_cli, get_batch_client
from aws_deploy.batch.helper import BatchError


@batch_cli.command()
@click.argument('job-definition-name')
@click.option('--tag', help='New tag to apply to the image defined in the job definition')
@click.option('--deregister/--no-deregister', default=False, show_default=True, help='Deregister or keep the old task definitions.')  # noqa: E501
@click.pass_context
def deploy(ctx, job_definition_name, tag, deregister):
    """
    Deploys a job definition revision.

    \b
    JOB_DEFINITION_NAME is the name of an AWS Batch Job definition.
    """

    try:
        click.secho(f'Deploy [job_definition_name={job_definition_name}]')
        batch_client = get_batch_client(ctx)

        # fetch job definition
        click.secho(f'Fetching job definition [job_definition_name={job_definition_name}] -> ', nl=False)
        selected_job_definition = batch_client.get_job_definition(job_definition_name=job_definition_name)
        click.secho(f'{selected_job_definition.arn}', fg='green')

        # selected tag
        if tag:
            selected_tag = tag
        else:
            selected_tag = selected_job_definition.container_properties.image.rsplit(':', 1)[1]

        # skip latest tag
        if 'latest' in selected_tag:
            last_jobs_definition = batch_client.get_last_jobs_definition(
                job_definition_name=job_definition_name, count=5
            )

            for last_job_definition in last_jobs_definition:
                last_image = last_job_definition.container_properties.image
                last_tag = last_image.rsplit(':', 1)[1]

                if 'latest' not in last_tag:
                    selected_tag = last_tag
                    break

            if 'latest' in selected_tag:
                raise BatchError('Cannot find valid tag')

        selected_container_properties = selected_job_definition.container_properties
        selected_container_properties.set_image(tag=selected_tag)

        if selected_job_definition.updated:
            selected_job_definition.set_tag('Terraform', 'false')
            selected_job_definition.set_tag('ImageTag', selected_tag)
            selected_job_definition.show_diff(show_diff=True)

            click.secho('Creating new job definition revision -> ', nl=False)
            new_job_definition = batch_client.register_job_definition(job_definition=selected_job_definition)
            click.secho(f'{new_job_definition.revision}', fg='green')
        else:
            click.secho('No changes required, job definition is up to date!', fg='green')
            new_job_definition = selected_job_definition

        if deregister:
            keep_count = 3
            click.secho(f'Deregister old task definitions, keeping last {keep_count}', fg='blue')
            jobs_definition = batch_client.get_last_jobs_definition(
                job_definition_name=job_definition_name, count=10
            )
            jobs_definition = list(filter(
                lambda x: not strtobool(x.get_tag('Terraform')),
                jobs_definition
            ))[keep_count:]

            for job_definition in jobs_definition:
                click.secho(f'Deregister job definition revision: {job_definition.revision}', fg='red')
                batch_client.deregister_job_definition(job_definition.arn)

    except BatchError as e:
        click.secho(str(e), fg='red', err=True)
        exit(1)
