import click
from boto3 import Session
from boto3_type_annotations import batch


class Diff:
    def __init__(self, field, value, old_value):
        self.field = field
        self.value = value
        self.old_value = old_value

    def __repr__(self):
        return f'Changed {self.field} to: "{self.value}" (was: "{self.old_value}")'


class BatchJobDefinition:
    def __init__(self, jobDefinitionName, jobDefinitionArn, revision, status=None, containerProperties=None, tags=None,
                 **kwargs):
        self.job_definition_name = jobDefinitionName
        self.arn = jobDefinitionArn
        self.revision = revision
        self.status = status
        self.container_properties = BatchContainerProperties(**containerProperties) if containerProperties else None
        self.tags = tags
        self.additional_properties = kwargs
        self._diff = []

    @property
    def updated(self) -> bool:
        return self._diff != [] or self.container_properties.updated

    def show_diff(self, show_diff: bool = False):
        if show_diff:
            click.secho('Job Definition modified:')
            for diff in self._diff:
                click.secho(f'    {str(diff)}', fg='blue')
            click.secho('')

            self.container_properties.show_diff(show_diff=show_diff)

    def set_tag(self, key: str, value: str):
        if key and value:
            if key in self.tags:
                if self.tags[key] != value:
                    diff = Diff(
                        field=f"tags['{key}']",
                        value=value,
                        old_value=self.tags[key]
                    )
                    self._diff.append(diff)
                    self.tags[key] = value
            else:
                diff = Diff(field=f"tags['{key}']", value=value, old_value=None)
                self._diff.append(diff)
                self.tags[key] = value


class BatchContainerProperties:
    def __init__(self, image, **kwargs):
        self.image = image
        self.additional_properties = kwargs
        self._diff = []

    @property
    def updated(self) -> bool:
        return self._diff != []

    def show_diff(self, show_diff: bool = False):
        if show_diff:
            click.secho('Container Properties modified:')
            for diff in self._diff:
                click.secho(f'    {str(diff)}', fg='blue')
            click.secho('')

    def set_image(self, tag=None, image=None):
        if image:
            new_image = image
        elif tag:
            new_image = self.image.rsplit(':', 1)
            new_image = f'{new_image[0]}:{tag.strip()}'
        else:
            new_image = None

        # check if tag changes
        if new_image and new_image != self.image:
            diff = Diff(
                field='image',
                value=new_image,
                old_value=self.image
            )
            self._diff.append(diff)
            self.image = new_image


class BatchClient:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None, region_name=None,
                 profile_name=None):
        session = Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
            profile_name=profile_name
        )

        self._batch: batch.Client = session.client('batch')

    def get_job_definition(self, job_definition_name: str) -> BatchJobDefinition:
        job_definition_payload = self._batch.describe_job_definitions(
            jobDefinitionName=job_definition_name,
            status='ACTIVE'
        )

        job_definitions = sorted(
            job_definition_payload['jobDefinitions'],
            key=lambda x: x['revision'],
            reverse=True
        )

        if len(job_definitions) > 0:
            # Fetch last active revision
            return BatchJobDefinition(
                **job_definitions[0]
            )

        raise UnknownJobDefinitionError(f'Job definition not found [Name={job_definition_name}]')

    def get_last_job_definition(self, job_definition_name: str) -> BatchJobDefinition:
        def filter_latest_tag(definition):
            container_properties = definition['containerProperties']
            image = container_properties['image']
            tag = image.rsplit(':', 1)[1]

            return tag != 'latest'

        job_definition_payload = self._batch.describe_job_definitions(
            jobDefinitionName=job_definition_name,
            status='ACTIVE'
        )

        job_definitions = filter(
            filter_latest_tag,
            job_definition_payload['jobDefinitions']
        )

        job_definitions = sorted(
            job_definitions,
            key=lambda x: x['revision'],
            reverse=True
        )

        if len(job_definitions) > 0:
            # Fetch last active revision
            return BatchJobDefinition(
                **job_definitions[0]
            )

        raise UnknownJobDefinitionError(f'Job definition not found [Name={job_definition_name}]')

    def register_job_definition(self, job_definition: BatchJobDefinition):
        if job_definition.tags:
            job_definition.additional_properties['tags'] = job_definition.tags

        new_job_definition_payload = self._batch.register_job_definition(
            jobDefinitionName=job_definition.job_definition_name,
            containerProperties={
                'image': job_definition.container_properties.image,
                **job_definition.container_properties.additional_properties
            },
            **job_definition.additional_properties
        )

        return BatchJobDefinition(**new_job_definition_payload)

    def deregister_job_definition(self, job_definition_arn: str):
        return self._batch.deregister_job_definition(
            jobDefinition=job_definition_arn
        )


class BatchError(Exception):
    pass


class UnknownJobDefinitionError(BatchError):
    pass
