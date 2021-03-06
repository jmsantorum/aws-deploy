import hashlib
import json
from typing import List, Optional

import click
from boto3 import Session
from boto3_type_annotations import codedeploy
from boto3_type_annotations import ecs
from boto3_type_annotations import resourcegroupstaggingapi
from botocore.exceptions import ClientError

from aws_deploy.ecs.helper import EcsTaskDefinition, EcsService


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
    def __init__(self, applicationName, deploymentGroupId, deploymentGroupName, deploymentConfigName,
                 targetRevision=None, ecsServices=None, **kwargs):
        self.application_name = applicationName
        self.deployment_group_id = deploymentGroupId
        self.deployment_group_name = deploymentGroupName
        self.deployment_config_name = deploymentConfigName
        self.target_revision = targetRevision
        self.cluster_name = None
        self.ecs_service_name = None

        if ecsServices:
            self.cluster_name = ecsServices[0]['clusterName']
            self.ecs_service_name = ecsServices[0]['serviceName']


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

    def get_task_definitions(self) -> List[str]:
        task_definitions = list()

        for resource in self.content_json['Resources']:
            target_service = resource['TargetService']
            properties = target_service['Properties']

            task_definitions.append(properties['TaskDefinition'])

        return task_definitions

    def get_task_definition(self, position: int = 0) -> str:
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

    def get_task_definitions(self) -> List[str]:
        task_definitions = list()

        for resource in self.content_json['Resources']:
            target_service = resource['TargetService']
            properties = target_service['Properties']

            task_definitions.append(properties['TaskDefinition'])

        return task_definitions

    def get_task_definition(self, position: int = 0) -> str:
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

    def get_application_revision(self, application_name: str, deployment_group: CodeDeployDeploymentGroup) -> Optional[CodeDeployApplicationRevision]:  # noqa E501
        if not deployment_group.target_revision:
            return None

        application_revision_payload = self._code_deploy.get_application_revision(
            applicationName=application_name,
            revision=deployment_group.target_revision
        )

        return CodeDeployApplicationRevision(
            **application_revision_payload
        )

    def get_task_definition_filtered(self, family: str, module_version: str):
        click.secho(f'Required Task [Family={family}, ModuleVersion={module_version}]')
        mayor_minor_version, patch_version = module_version.rsplit('.', 1)

        compatible_module_versions = [
            f'{mayor_minor_version}.{next_patch_version}'
            for next_patch_version in range(int(patch_version), int(patch_version) + 10)
        ]

        response_payload = self._resource_tagging.get_resources(
            ResourceTypeFilters=['ecs:task-definition'],
            TagFilters=[
                {'Key': 'Family', 'Values': [family]},
                {'Key': 'ModuleVersion', 'Values': compatible_module_versions}
            ]
        )

        task_definition_arns = sorted(
            [item['ResourceARN'] for item in response_payload['ResourceTagMappingList']],
            key=lambda x: int(x.rsplit(':', 1)[1]),  # sort by (int) version
            reverse=True
        )

        if task_definition_arns:
            task_definition = self.get_task_definition(task_definition_arn=task_definition_arns[0])
            module_version = task_definition.get_tag('ModuleVersion')
            click.secho(f'Found Task [Family={family}, ModuleVersion={module_version}]')
            return self.get_task_definition(task_definition_arn=task_definition_arns[0])

        raise UnknownTaskDefinitionError(f'Task not found [Family={family}, ModuleVersion={module_version}]')

    def get_last_tasks_definition(self, family: str, count: int = 1) -> List[EcsTaskDefinition]:
        response_payload = self._ecs.list_task_definitions(
            familyPrefix=family,
            status='ACTIVE',
            sort='DESC',
            maxResults=count
        )

        task_definition_arns = response_payload['taskDefinitionArns']

        if len(task_definition_arns) > 0:
            return list(
                map(
                    lambda task_definition_arn: self.get_task_definition(task_definition_arn), task_definition_arns
                )
            )

        raise UnknownTaskDefinitionError(f'Task definition not found [Family={family}]')

    def get_service(self, deployment_group: CodeDeployDeploymentGroup) -> EcsService:
        services_payload = self._ecs.describe_services(
            cluster=deployment_group.cluster_name,
            services=[deployment_group.ecs_service_name]
        )

        return EcsService(
            cluster=deployment_group.cluster_name,
            service_definition=services_payload['services'][0]
        )

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
        try:
            deployment_payload = self._code_deploy.create_deployment(
                applicationName=application_name,
                deploymentGroupName=deployment_group_name,
                revision=revision.to_dict()
            )

            return CodeDeployDeployment(
                deploymentId=deployment_payload['deploymentId'],
                applicationName=None, deploymentGroupName=None, deploymentConfigName=None, revision=None, status=None
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'DeploymentLimitExceededException':
                click.secho('There is an active deployment, waiting...')
                # TODO
            raise e

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

    def create_new_revision(self, task_definition: EcsTaskDefinition):
        container = task_definition.containers[0]
        container_name = container['name']
        container_port = container['portMappings'][0]['containerPort']

        app_spec_content = {
            "Resources": [
                {
                    "TargetService": {
                        "Type": "AWS::ECS::Service",
                        "Properties": {
                            "TaskDefinition": task_definition.arn,
                            "LoadBalancerInfo": {
                                "ContainerName": container_name,
                                "ContainerPort": container_port
                            },
                            "PlatformVersion": None
                        }
                    }
                }
            ]
        }

        return CodeDeployRevision(
            revisionType='AppSpecContent',
            appSpecContent={'content': json.dumps(app_spec_content, separators=(',', ':'))}
        )


class CodeDeployError(Exception):
    pass


class UnknownTaskDefinitionError(CodeDeployError):
    pass


class CodeDeployConnectionError(CodeDeployError):
    pass


class NotSupportedError(CodeDeployError):
    pass
