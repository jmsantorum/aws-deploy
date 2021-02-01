import hashlib
import json

import click
from boto3 import Session
from boto3_type_annotations import codedeploy
from boto3_type_annotations import ecs
from boto3_type_annotations import resourcegroupstaggingapi
from botocore.exceptions import ClientError

from aws_deploy.ecs.helper import EcsTaskDefinition


class Diff:
    def __init__(self, field, value, old_value):
        self.field = field
        self.value = value
        self.old_value = old_value

    def __repr__(self):
        return f'Changed {self.field} to: "{self.value}" (was: "{self.old_value}")'


class CodeDeployApplication:
    def __init__(self, applicationId, applicationName, **kwargs):
        self.application_id = applicationId
        self.application_name = applicationName


class CodeDeployDeploymentGroup:
    def __init__(self, applicationName, deploymentGroupId, deploymentGroupName, deploymentConfigName, targetRevision,
                 **kwargs):
        self.application_name = applicationName
        self.deployment_group_id = deploymentGroupId
        self.deployment_group_name = deploymentGroupName
        self.deployment_config_name = deploymentConfigName
        self.target_revision = targetRevision


class CodeDeployString:
    def __init__(self, string):
        content_raw = string.get('content', '{}')
        sha256_raw = string.get('sha256', hashlib.sha256(content_raw.encode()).hexdigest())

        self.content_json = json.loads(content_raw)
        self.sha256 = sha256_raw
        self._diff = []

    @property
    def updated(self) -> bool:
        return self._diff != []

    def show_diff(self, show_diff: bool = False):
        if show_diff:
            click.secho('String modified:')
            for diff in self._diff:
                click.secho(f'    {str(diff)}', fg='blue')
            click.secho('')

    def to_dict(self):
        content_str = json.dumps(self.content_json, separators=(',', ':'))
        sha256 = hashlib.sha256(content_str.encode()).hexdigest()

        return {
            'content': content_str,
            'sha256': sha256
        }

    def get_task_definitions(self):
        task_definitions = list()

        for resource in self.content_json['Resources']:
            target_service = resource['TargetService']
            properties = target_service['Properties']

            task_definitions.append(properties['TaskDefinition'])

        return task_definitions

    def get_task_definition(self, position: int = 0):
        task_definitions = self.get_task_definitions()

        return task_definitions[position]

    def set_task_definition(self, new_task_definition: EcsTaskDefinition):
        for resource in self.content_json['Resources']:
            target_service = resource['TargetService']
            properties = target_service['Properties']

            old_task_definition = properties['TaskDefinition']
            if new_task_definition.arn != old_task_definition:
                diff = Diff(field='TaskDefinition', value=new_task_definition.arn, old_value=old_task_definition)
                self._diff.append(diff)
                properties['TaskDefinition'] = new_task_definition.arn


class CodeDeployAppSpecContent:
    def __init__(self, app_spec_content):
        content_raw = app_spec_content.get('content', '{}')
        sha256_raw = app_spec_content.get('sha256', hashlib.sha256(content_raw.encode()).hexdigest())

        self.content_json = json.loads(content_raw)
        self.sha256 = sha256_raw
        self._diff = []

    @property
    def updated(self) -> bool:
        return self._diff != []

    def show_diff(self, show_diff: bool = False):
        if show_diff:
            click.secho('App Spec Content modified:')
            for diff in self._diff:
                click.secho(f'    {str(diff)}', fg='blue')
            click.secho('')

    def to_dict(self):
        content_str = json.dumps(self.content_json, separators=(',', ':'))
        sha256 = hashlib.sha256(content_str.encode()).hexdigest()

        return {
            'content': content_str,
            'sha256': sha256
        }

    def get_task_definitions(self):
        task_definitions = list()

        for resource in self.content_json['Resources']:
            target_service = resource['TargetService']
            properties = target_service['Properties']

            task_definitions.append(properties['TaskDefinition'])

        return task_definitions

    def get_task_definition(self, position: int = 0):
        task_definitions = self.get_task_definitions()

        return task_definitions[position]

    def set_task_definition(self, new_task_definition: EcsTaskDefinition):
        for resource in self.content_json['Resources']:
            target_service = resource['TargetService']
            properties = target_service['Properties']

            old_task_definition = properties['TaskDefinition']
            if new_task_definition.arn != old_task_definition:
                diff = Diff(field='TaskDefinition', value=new_task_definition.arn, old_value=old_task_definition)
                self._diff.append(diff)
                properties['TaskDefinition'] = new_task_definition.arn


class CodeDeployRevision:
    def __init__(self, revisionType, s3Location=None, gitHubLocation=None, string=None, appSpecContent=None, **kwargs):
        self.revision_type = revisionType
        self.s3_location = s3Location
        self.github_location = gitHubLocation
        self.string: CodeDeployString = CodeDeployString(string) if self.revision_type == 'String' else None
        self.app_spec_content: CodeDeployAppSpecContent = (
            CodeDeployAppSpecContent(appSpecContent) if self.revision_type == 'AppSpecContent' else None
        )
        self._diff = []

        if self.revision_type not in ['String', 'AppSpecContent']:
            raise NotSupportedError(f"Revision type '{self.revision_type}' not supported!")

    @property
    def updated(self) -> bool:
        updated = self._diff != []

        if self.string:
            updated |= self.string.updated

        if self.app_spec_content:
            updated |= self.app_spec_content.updated

        return updated

    def show_diff(self, show_diff: bool = False):
        if show_diff:
            click.secho('Revision modified:')
            for diff in self._diff:
                click.secho(f'    {str(diff)}', fg='blue')
            click.secho('')

            if self.string:
                self.string.show_diff(show_diff=show_diff)

            if self.app_spec_content:
                self.app_spec_content.show_diff(show_diff=show_diff)

    def to_dict(self):
        result = {'revisionType': self.revision_type}

        if self.s3_location:
            result['s3Location'] = self.s3_location

        if self.github_location:
            result['gitHubLocation'] = self.github_location

        if self.string:
            result['string'] = self.string.to_dict()

        if self.app_spec_content:
            result['appSpecContent'] = self.app_spec_content.to_dict()

        return result

    def set_task_definition(self, new_task_definition: EcsTaskDefinition):
        if self.string:
            self.string.set_task_definition(new_task_definition=new_task_definition)
        elif self.app_spec_content:
            self.app_spec_content.set_task_definition(new_task_definition=new_task_definition)

    def get_task_definition(self):
        if self.string:
            current_task_definition = self.string.get_task_definition()
        elif self.app_spec_content:
            current_task_definition = self.app_spec_content.get_task_definition()
        else:
            current_task_definition = None

        return current_task_definition


class CodeDeployApplicationRevision:
    def __init__(self, applicationName, revision, **kwargs):
        self.application_name = applicationName
        self.revision: CodeDeployRevision = CodeDeployRevision(**revision)
        self._diff = []

    @property
    def updated(self) -> bool:
        return self._diff != [] or self.revision.updated

    def show_diff(self, show_diff: bool = False):
        if show_diff:
            click.secho('Application revision modified:')
            for diff in self._diff:
                click.secho(f'    {str(diff)}', fg='blue')
            click.secho('')

            self.revision.show_diff(show_diff=show_diff)

    def set_task_definition(self, new_task_definition: EcsTaskDefinition):
        self.revision.set_task_definition(new_task_definition=new_task_definition)


class CodeDeployDeployment:
    def __init__(self, deploymentId, applicationName, deploymentGroupName, deploymentConfigName, revision, status,
                 errorInformation=None, **kwargs):
        self.deployment_id = deploymentId
        self.application_name = applicationName
        self.deployment_group_name = deploymentGroupName
        self.deployment_config_name = deploymentConfigName
        self.revision = revision
        self.status = status
        self.error_info = errorInformation

    # ['Created', 'Queued', 'InProgress', 'Baking', 'Succeeded', 'Failed', 'Stopped', 'Ready']

    def is_waiting(self) -> bool:
        return self.status in ['Created', 'Queued', 'InProgress', 'Baking', 'Ready']

    def is_success(self) -> bool:
        return self.status in ['Succeeded']

    def is_error(self) -> bool:
        return self.status in ['Failed', 'Stopped']


class CodeDeployClient:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None, region_name=None,
                 profile_name=None):
        session = Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
            profile_name=profile_name
        )

        self._code_deploy: codedeploy.Client = session.client('codedeploy')
        self._ecs: ecs.Client = session.client('ecs')
        self._resource_tagging: resourcegroupstaggingapi.Client = session.client('resourcegroupstaggingapi')

    def get_application(self, application_name: str) -> CodeDeployApplication:
        application_payload = self._code_deploy.get_application(
            applicationName=application_name
        )

        return CodeDeployApplication(
            **application_payload['application']
        )

    def get_deployment_group(self, application_name: str, deployment_group_name: str) -> CodeDeployDeploymentGroup:
        deployment_group_payload = self._code_deploy.get_deployment_group(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name
        )

        return CodeDeployDeploymentGroup(
            **deployment_group_payload['deploymentGroupInfo']
        )

    def get_application_revision(self, application_name: str,
                                 deployment_group: CodeDeployDeploymentGroup) -> CodeDeployApplicationRevision:  # noqa E501
        application_revision_payload = self._code_deploy.get_application_revision(
            applicationName=application_name,
            revision=deployment_group.target_revision
        )

        return CodeDeployApplicationRevision(
            **application_revision_payload
        )

    def get_task_definition_filtered(self, family: str, module_version: str):
        response_payload = self._resource_tagging.get_resources(
            ResourceTypeFilters=['ecs:task-definition'],
            TagFilters=[
                {'Key': 'Family', 'Values': [family]},
                {'Key': 'ModuleVersion', 'Values': [module_version]}
            ]
        )

        task_definition_arns = sorted(
            [item['ResourceARN'] for item in response_payload['ResourceTagMappingList']], reverse=True
        )

        if task_definition_arns:
            return self.get_task_definition(task_definition_arn=task_definition_arns[0])

        raise UnknownTaskDefinitionError(f'Task not found [Family={family}, ModuleVersion={module_version}]')

    def get_task_definition(self, task_definition_arn: str) -> EcsTaskDefinition:
        try:
            task_definition_payload = self._ecs.describe_task_definition(
                taskDefinition=task_definition_arn,
                include=[
                    'TAGS',
                ]
            )

            return EcsTaskDefinition(
                tags=task_definition_payload.get('tags', None), **task_definition_payload['taskDefinition']
            )
        except ClientError as e:
            raise UnknownTaskDefinitionError(str(e))

    def create_deployment(self, application_name: str, deployment_group_name: str,
                          revision: CodeDeployRevision) -> CodeDeployDeployment:  # noqa: E501
        deployment_payload = self._code_deploy.create_deployment(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name,
            revision=revision.to_dict()
        )

        return CodeDeployDeployment(
            deploymentId=deployment_payload['deploymentId'],
            applicationName=None, deploymentGroupName=None, deploymentConfigName=None, revision=None, status=None
        )

    def get_deployment(self, deployment_id: str) -> CodeDeployDeployment:
        deployment_payload = self._code_deploy.get_deployment(
            deploymentId=deployment_id
        )

        return CodeDeployDeployment(
            **deployment_payload['deploymentInfo']
        )

    def register_task_definition(self, task_definition: EcsTaskDefinition):
        if task_definition.tags:
            task_definition.additional_properties['tags'] = task_definition.tags

        new_task_definition_payload = self._ecs.register_task_definition(
            family=task_definition.family,
            containerDefinitions=task_definition.containers,
            volumes=task_definition.volumes,
            taskRoleArn=task_definition.role_arn,
            executionRoleArn=task_definition.execution_role_arn,
            **task_definition.additional_properties
        )

        return EcsTaskDefinition(**new_task_definition_payload['taskDefinition'])

    def deregister_task_definition(self, task_definition_arn: str):
        return self._ecs.deregister_task_definition(
            taskDefinition=task_definition_arn
        )


class CodeDeployError(Exception):
    pass


class UnknownTaskDefinitionError(CodeDeployError):
    pass


class CodeDeployConnectionError(CodeDeployError):
    pass


class NotSupportedError(CodeDeployError):
    pass
