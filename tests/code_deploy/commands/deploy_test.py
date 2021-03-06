from datetime import datetime

import pytest
from click.testing import CliRunner
from mock import patch

from aws_deploy.code_deploy.commands import deploy
from tests.code_deploy.utils import CodeDeployTestClient


@pytest.fixture
def runner():
    return CliRunner()


@patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
def test_deploy_without_credentials(get_code_deploy_client, runner):
    get_code_deploy_client.return_value = CodeDeployTestClient()
    result = runner.invoke(deploy.deploy, ('test-application', 'test-deployment-group'))

    assert result.exit_code == 1

    assert 'Unable to locate credentials' in result.output


@patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
def test_deploy_wit_invalid_application(get_code_deploy_client, runner):
    get_code_deploy_client.return_value = CodeDeployTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, ('unknown-application', 'test-deployment-group'))

    assert result.exit_code == -1
    assert result.exception

    assert 'No application found for name: unknown-application' in str(result.exception)


@patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
def test_deploy_wit_invalid_deployment_group(get_code_deploy_client, runner):
    get_code_deploy_client.return_value = CodeDeployTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, ('test-application', 'unknown-deployment-group'))

    assert result.exit_code == -1
    assert result.exception

    assert 'No Deployment Group found for name: unknown-deployment-group' in str(result.exception)


@patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
def test_deploy_wit_invalid_application_revision(get_code_deploy_client, runner):
    # TODO
    pass


# @patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
# def test_deploy(get_code_deploy_client, runner):
#     get_code_deploy_client.return_value = CodeDeployTestClient('access_key', 'secret_key')
#     result = runner.invoke(deploy.deploy, ('test-application', 'test-deployment-group'))
#
#     assert result.exit_code == 0
#
#     assert 'Deploy [application_name=test-application, deployment_group_name=test-deployment-group]' in result.output
#     assert 'Deploying new application revision' in result.output
#     assert 'Deployment successful' in result.output


# @patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
# def test_deploy_with_timeout(get_code_deploy_client, runner):
#     get_code_deploy_client.return_value = CodeDeployTestClient('access_key', 'secret_key', wait=1)
#     result = runner.invoke(deploy.deploy, ('test-application', 'test-deployment-group', '--timeout', '2'))
#
#     assert result.exit_code == 0
#
#     assert 'Deploy [application_name=test-application, deployment_group_name=test-deployment-group]' in result.output
#     assert 'Deploying new application revision' in result.output
#     assert 'Deployment successful' in result.output


# @patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
# def test_deploy_with_wait_within_timeout(get_code_deploy_client, runner):
#     get_code_deploy_client.return_value = CodeDeployTestClient('access_key', 'secret_key', wait=2)
#     result = runner.invoke(deploy.deploy, ('test-application', 'test-deployment-group', '--timeout', '5'))
#
#     assert result.exit_code == 0
#
#     assert 'Deploy [application_name=test-application, deployment_group_name=test-deployment-group]' in result.output
#     assert 'Deploying new application revision..' in result.output
#     assert 'Deployment successful' in result.output


# @patch('aws_deploy.code_deploy.commands.deploy.get_code_deploy_client')
# def test_deploy_without_timeout(get_code_deploy_client, runner):
#     get_code_deploy_client.return_value = CodeDeployTestClient('access_key', 'secret_key')
#
#     start_time = datetime.now()
#     result = runner.invoke(deploy.deploy, ('test-application', 'test-deployment-group', '--timeout', '-1'))
#     end_time = datetime.now()
#
#     assert result.exit_code == 0
#
#     # assert task is not waiting for deployment
#     assert 'Deploy [application_name=test-application, deployment_group_name=test-deployment-group]' in result.output
#     assert 'Deploying new application revision' in result.output
#     assert '..' not in result.output
#     assert 'Deployment successful' in result.output
#     assert (end_time - start_time).total_seconds() < 1
