import pytest
from boto3 import Session
from botocore.exceptions import ClientError
from mock import patch

from aws_deploy.code_deploy.helper import (
    CodeDeployClient, UnknownTaskDefinitionError, CodeDeployDeploymentGroup, CodeDeployRevision
)
from tests.code_deploy.utils import (
    DEPLOYMENT_ID, APPLICATION_PAYLOAD, DEPLOYMENT_GROUP_PAYLOAD, APPLICATION_REVISION_PAYLOAD, TASK_DEFINITION_PAYLOAD,
    DEPLOYMENT_PAYLOAD
)


@patch.object(Session, 'client')
@patch.object(Session, '__init__')
def test_client_init(mocked_init, mocked_client):
    mocked_init.return_value = None

    CodeDeployClient('access_key_id', 'secret_access_key', 'session_token', 'region_name', 'profile_name')

    mocked_init.assert_called_once_with(
        aws_access_key_id='access_key_id',
        aws_secret_access_key='secret_access_key',
        aws_session_token='session_token',
        region_name='region_name',
        profile_name='profile_name'
    )

    mocked_client.assert_any_call('codedeploy')
    mocked_client.assert_any_call('ecs')


@pytest.fixture
@patch.object(Session, 'client')
@patch.object(Session, '__init__')
def client(mocked_init, mocked_client) -> CodeDeployClient:
    mocked_init.return_value = None

    return CodeDeployClient('access_key_id', 'secret_access_key', 'session_token', 'region_name', 'profile_name')


def test_client_get_application(client: CodeDeployClient):
    client._code_deploy.get_application.return_value = APPLICATION_PAYLOAD

    client.get_application('test-application')
    client._code_deploy.get_application.assert_called_once_with(applicationName='test-application')


def test_client_get_deployment_group(client: CodeDeployClient):
    client._code_deploy.get_deployment_group.return_value = DEPLOYMENT_GROUP_PAYLOAD
    client.get_deployment_group('test-application', 'test-deployment-group')
    client._code_deploy.get_deployment_group.assert_called_once_with(
        applicationName='test-application',
        deploymentGroupName='test-deployment-group'
    )


def test_client_get_application_revision(client: CodeDeployClient):
    deployment_group = CodeDeployDeploymentGroup(
        **DEPLOYMENT_GROUP_PAYLOAD['deploymentGroupInfo']
    )

    client._code_deploy.get_application_revision.return_value = APPLICATION_REVISION_PAYLOAD

    client.get_application_revision('test-application', deployment_group)
    client._code_deploy.get_application_revision.assert_called_once_with(
        applicationName='test-application',
        revision={
            'revisionType': deployment_group.target_revision['revisionType'],
            'appSpecContent': deployment_group.target_revision['appSpecContent']
        }
    )


def test_client_get_task_definition(client: CodeDeployClient):
    client._ecs.describe_task_definition.return_value = TASK_DEFINITION_PAYLOAD

    client.get_task_definition('task-definition-arn')
    client._ecs.describe_task_definition.assert_called_once_with(
        taskDefinition='task-definition-arn',
        include=[
            'TAGS',
        ]
    )


def test_client_get_unknown_task_definition(client: CodeDeployClient):
    error_response = {'Error': {'Code': 'ClientException', 'Message': 'Unable to describe task definition.'}}
    client._ecs.describe_task_definition.side_effect = ClientError(error_response, 'DescribeServices')

    with pytest.raises(UnknownTaskDefinitionError):
        client.get_task_definition('task_definition_arn')


def test_create_deployment(client: CodeDeployClient):
    revision = CodeDeployRevision(
        revisionType='AppSpecContent', appSpecContent=dict()
    )

    client._code_deploy.create_deployment.return_value = {'deploymentId': DEPLOYMENT_ID}
    client.create_deployment('test-application', 'test-deployment-group', revision)
    client._code_deploy.create_deployment.assert_called_once_with(
        applicationName='test-application',
        deploymentGroupName='test-deployment-group',
        revision=revision.to_dict()
    )


def test_client_get_deployment(client: CodeDeployClient):
    client._code_deploy.get_deployment.return_value = DEPLOYMENT_PAYLOAD

    client.get_deployment('deployment-id')
    client._code_deploy.get_deployment.assert_called_once_with(deploymentId='deployment-id')
