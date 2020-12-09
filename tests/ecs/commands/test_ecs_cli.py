from datetime import datetime

import pytest
from click.testing import CliRunner
from mock import patch, Mock

from aws_deploy.ecs import cli
from aws_deploy.ecs.cli import get_ecs_client
from aws_deploy.ecs.commands import diff, cron, update, run, scale, deploy
from aws_deploy.ecs.helper import EcsClient
from tests.ecs.utils import EcsTestClient
from tests.ecs.constants import (
    CLUSTER_NAME, SERVICE_NAME, TASK_DEFINITION_ARN_2, TASK_DEFINITION_ARN_1, TASK_DEFINITION_FAMILY_1,
    TASK_DEFINITION_REVISION_1, TASK_DEFINITION_REVISION_3
)


@pytest.fixture
def runner():
    return CliRunner()


@patch.object(EcsClient, '__init__')
def test_get_client(ecs_client):
    ecs_client.return_value = None
    ctx = Mock()
    ctx.obj = {
        'AWS_ACCESS_KEY_ID': 'access_key_id',
        'AWS_SECRET_ACCESS_KEY': 'secret_access_key',
        'AWS_SESSION_TOKEN': 'aws_session_token',
        'AWS_REGION': 'region',
        'AWS_PROFILE': 'profile'
    }
    client = get_ecs_client(ctx)
    ecs_client.assert_called_once_with(
        aws_access_key_id='access_key_id',
        aws_secret_access_key='secret_access_key',
        aws_session_token='aws_session_token',
        region_name='region',
        profile_name='profile'
    )
    assert isinstance(client, EcsClient)


def test_ecs(runner):
    result = runner.invoke(cli.ecs_cli)
    assert result.exit_code == 0
    assert not result.exception
    assert 'Usage: ecs [OPTIONS] COMMAND [ARGS]' in result.output
    assert '  deploy  ' in result.output
    assert '  scale   ' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_without_credentials(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient()
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME))

    assert result.exit_code == 1

    assert u'Unable to locate credentials. Configure credentials by running "aws configure".\n' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_invalid_cluster(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, ('unknown-cluster', SERVICE_NAME))

    assert result.exit_code == 1

    assert u'An error occurred (ClusterNotFoundException) when calling the DescribeServices ' \
           u'operation: Cluster not found.\n' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_invalid_service(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, 'unknown-service'))

    assert result.exit_code == 1

    assert u'An error occurred when calling the DescribeServices operation: Service not found.\n' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output
    assert u"Updating task definition" not in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_rollback(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', wait=2)
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--timeout=1', '--rollback'))

    assert result.exit_code == 1
    assert result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output

    assert u"Deployment failed" in result.output
    assert u"Rolling back to task definition: test-task:1" in result.output
    assert u'Successfully changed task definition to: test-task:1' in result.output

    assert u"Rollback successful" in result.output
    assert u'Deployment failed, but service has been rolled back to ' \
           u'previous task definition: test-task:1' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_without_deregister(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--no-deregister'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' not in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output
    assert u"Updating task definition" not in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_role_arn(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-r', 'arn:new:role'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed role_arn to: "arn:new:role" (was: "arn:test:role:1")' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_execution_role_arn(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-x', 'arn:new:role'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed execution_role_arn to: "arn:new:role" (was: "arn:test:role:1")' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_new_tag(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-t', 'latest'))

    assert result.exit_code == 0
    assert not result.exception

    assert "Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert "Updating task definition" in result.output
    assert 'Changed image of container "webserver" to: "webserver:latest" (was: "webserver:123")' in result.output
    assert 'Changed image of container "application" to: "application:latest" (was: "application:123")' in result.output
    assert 'Successfully created revision: 2' in result.output
    assert 'Successfully deregistered revision: 1' in result.output
    assert 'Successfully changed task definition to: test-task:2' in result.output
    assert 'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_one_new_image(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-i', 'application', 'application:latest'))

    assert result.exit_code == 0
    assert not result.exception

    assert "Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert "Updating task definition" in result.output
    assert 'Changed image of container "application" to: "application:latest" (was: "application:123")' in result.output
    assert 'Successfully created revision: 2' in result.output
    assert 'Successfully deregistered revision: 1' in result.output
    assert 'Successfully changed task definition to: test-task:2' in result.output
    assert 'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_two_new_images(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy,
        (CLUSTER_NAME, SERVICE_NAME, '-i', 'application', 'application:latest', '-i', 'webserver', 'webserver:latest')
    )
    assert result.exit_code == 0
    assert not result.exception

    assert "Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert "Updating task definition" in result.output
    assert 'Changed image of container "webserver" to: "webserver:latest" (was: "webserver:123")' in result.output
    assert 'Changed image of container "application" to: "application:latest" (was: "application:123")' in result.output
    assert 'Successfully created revision: 2' in result.output
    assert 'Successfully deregistered revision: 1' in result.output
    assert 'Successfully changed task definition to: test-task:2' in result.output
    assert 'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_one_new_command(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-c', 'application', 'foobar'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed command of container "application" to: "foobar" (was: "run")' in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_one_new_environment_variable(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'application', 'foo', 'bar', '-e', 'webserver', 'foo', 'baz')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "foo" of container "application" to: "bar"' in result.output
    assert u'Changed environment "foo" of container "webserver" to: "baz"' in result.output
    assert u'Changed environment "lorem" of container "webserver" to: "ipsum"' not in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_change_environment_variable_empty_string(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'application', 'foo', ''))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "foo" of container "application" to: ""' in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_new_empty_environment_variable(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'application', 'new', ''))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "new" of container "application" to: ""' in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_empty_environment_variable_again(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'webserver', 'empty', ''))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed environment' not in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_previously_empty_environment_variable_with_value(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'webserver', 'empty', 'not-empty'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "empty" of container "webserver" to: "not-empty"' in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_exclusive_environment(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'webserver', 'new-env', 'new-value', '--exclusive-env')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "new-env" of container "webserver" to: "new-value"' in result.output

    assert u'Removed environment "foo" of container "webserver"' in result.output
    assert u'Removed environment "lorem" of container "webserver"' in result.output

    assert u'Removed secret' not in result.output

    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_exclusive_secret(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-s', 'webserver', 'new-secret', 'new-place', '--exclusive-secrets')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed secret "new-secret" of container "webserver" to: "new-place"' in result.output

    assert u'Removed secret "baz" of container "webserver"' in result.output
    assert u'Removed secret "dolor" of container "webserver"' in result.output

    assert u'Removed environment' not in result.output

    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_one_new_secret_variable(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-s', 'application', 'baz', 'qux', '-s', 'webserver', 'baz', 'quux')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed secret "baz" of container "application" to: "qux"' in result.output
    assert u'Changed secret "baz" of container "webserver" to: "quux"' in result.output
    assert u'Changed secret "dolor" of container "webserver" to: "sit"' not in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_without_changing_environment_value(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-e', 'webserver', 'foo', 'bar'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed environment' not in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_without_changing_secrets_value(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-s', 'webserver', 'baz', 'qux'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed secrets' not in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_without_diff(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '-t', 'latest', '-e', 'webserver', 'foo', 'barz', '--no-diff')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed environment' not in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_errors(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', deployment_errors=True)
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME))

    assert result.exit_code == 1

    assert u"Deployment failed" in result.output
    assert u"ERROR: Service was unable to Lorem Ipsum" in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_client_errors(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('acces_key', 'secret_key', client_errors=True)
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME))

    assert result.exit_code == 1

    assert u"Something went wrong" in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_ignore_warnings(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', deployment_errors=True)
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--ignore-warnings'))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Successfully deregistered revision: 1' in result.output
    assert u'Successfully changed task definition to: test-task:2' in result.output
    assert u"WARNING: Service was unable to Lorem Ipsum" in result.output
    assert u"Continuing." in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_task_definition_arn(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--task', TASK_DEFINITION_ARN_2))

    assert result.exit_code == 0
    assert not result.exception

    assert u"Deploy [cluster=test-cluster, service=test-service]" in result.output
    assert u'Successfully deregistered revision: 2' in result.output
    assert u'Deployment successful' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_timeout(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', wait=2)
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--timeout', '1'))

    assert result.exit_code == 1

    assert u"Deployment failed due to timeout. Please see:" in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_with_wait_within_timeout(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', wait=2)
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--timeout', '10'))
    assert result.exit_code == 0
    assert u'Deploying new task definition...' in result.output


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_without_timeout(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', wait=2)

    start_time = datetime.now()
    result = runner.invoke(deploy.deploy, (CLUSTER_NAME, SERVICE_NAME, '--timeout', '-1'))
    end_time = datetime.now()

    assert result.exit_code == 0

    # assert task is not waiting for deployment
    assert u'Deploying new task definition\n' in result.output
    assert u'...' not in result.output
    assert (end_time - start_time).total_seconds() < 1


@patch('aws_deploy.ecs.commands.deploy.get_ecs_client')
def test_deploy_unknown_task_definition_arn(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        deploy.deploy,
        (CLUSTER_NAME, SERVICE_NAME, '--task', u'arn:aws:ecs:eu-central-1:123456789012:task-definition/foobar:55')
    )

    assert result.exit_code == 1

    assert u"Unknown task definition arn: arn:aws:ecs:eu-central-1:123456789012:task-definition/foobar:55" \
           in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_without_credentials(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient()
    result = runner.invoke(scale.scale, (CLUSTER_NAME, SERVICE_NAME, '2'))

    assert result.exit_code == 1

    assert u'Unable to locate credentials. Configure credentials by running "aws configure".\n' in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_with_invalid_cluster(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(scale.scale, ('unknown-cluster', SERVICE_NAME, '2'))

    assert result.exit_code == 1

    assert u'An error occurred (ClusterNotFoundException) when calling the DescribeServices ' \
           u'operation: Cluster not found.\n' in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_with_invalid_service(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(scale.scale, (CLUSTER_NAME, 'unknown-service', '2'))

    assert result.exit_code == 1

    assert u'An error occurred when calling the DescribeServices operation: Service not found.\n' in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(scale.scale, (CLUSTER_NAME, SERVICE_NAME, '2'))

    assert not result.exception
    assert result.exit_code == 0

    assert u"Successfully updated desired count to: 2" in result.output
    assert u"Scaling successful" in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_with_errors(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', deployment_errors=True)
    result = runner.invoke(scale.scale, (CLUSTER_NAME, SERVICE_NAME, '2'))

    assert result.exit_code == 1

    assert u"Scaling failed" in result.output
    assert u"ERROR: Service was unable to Lorem Ipsum" in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_with_client_errors(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', client_errors=True)
    result = runner.invoke(scale.scale, (CLUSTER_NAME, SERVICE_NAME, '2'))

    assert result.exit_code == 1

    assert u"Something went wrong" in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_ignore_warnings(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', deployment_errors=True)
    result = runner.invoke(scale.scale, (CLUSTER_NAME, SERVICE_NAME, '2', '--ignore-warnings'))

    assert not result.exception
    assert result.exit_code == 0

    assert u"Successfully updated desired count to: 2" in result.output
    assert u"WARNING: Service was unable to Lorem Ipsum" in result.output
    assert u"Continuing." in result.output
    assert u"Scaling successful" in result.output


@patch('aws_deploy.ecs.commands.scale.get_ecs_client')
def test_scale_with_timeout(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', wait=2)
    result = runner.invoke(scale.scale, (CLUSTER_NAME, SERVICE_NAME, '2', '--timeout', '1'))

    assert result.exit_code == 1

    assert u"Scaling failed due to timeout. Please see:" in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(run.run, (CLUSTER_NAME, 'test-task'))

    assert not result.exception
    assert result.exit_code == 0

    assert u"Successfully started 2 instances of task: test-task:2" in result.output
    assert u"- arn:foo:bar" in result.output
    assert u"- arn:lorem:ipsum" in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task_with_command(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(run.run, (CLUSTER_NAME, 'test-task', '2', '-c', 'webserver', 'date'))

    assert not result.exception
    assert result.exit_code == 0

    assert u"Using task definition: test-task" in result.output
    assert u'Changed command of container "webserver" to: "date" (was: "run")' in result.output
    assert u"Successfully started 2 instances of task: test-task:2" in result.output
    assert u"- arn:foo:bar" in result.output
    assert u"- arn:lorem:ipsum" in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task_with_environment_var(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(run.run, (CLUSTER_NAME, 'test-task', '2', '-e', 'application', 'foo', 'bar'))

    assert not result.exception
    assert result.exit_code == 0

    assert u"Using task definition: test-task" in result.output
    assert u'Changed environment "foo" of container "application" to: "bar"' in result.output
    assert u"Successfully started 2 instances of task: test-task:2" in result.output
    assert u"- arn:foo:bar" in result.output
    assert u"- arn:lorem:ipsum" in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task_without_diff(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(run.run, (CLUSTER_NAME, 'test-task', '2', '-e', 'application', 'foo', 'bar', '--no-diff'))

    assert not result.exception
    assert result.exit_code == 0

    assert u"Using task definition: test-task" not in result.output
    assert u'Changed environment' not in result.output
    assert u"Successfully started 2 instances of task: test-task:2" in result.output
    assert u"- arn:foo:bar" in result.output
    assert u"- arn:lorem:ipsum" in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task_with_errors(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key', deployment_errors=True)
    result = runner.invoke(run.run, (CLUSTER_NAME, 'test-task'))

    assert result.exception
    assert result.exit_code == 1

    assert u"An error occurred (123) when calling the fake_error operation: Something went wrong" in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task_without_credentials(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient()
    result = runner.invoke(run.run, (CLUSTER_NAME, 'test-task'))

    assert result.exit_code == 1

    assert u'Unable to locate credentials. Configure credentials by running "aws configure".\n' in result.output


@patch('aws_deploy.ecs.commands.run.get_ecs_client')
def test_run_task_with_invalid_cluster(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(run.run, ('unknown-cluster', 'test-task'))

    assert result.exit_code == 1

    assert u"Run task [cluster=unknown-cluster, task=test-task]" in result.output
    assert u'An error occurred (ClusterNotFoundException) when calling the RunTask operation: Cluster not found.\n' \
           in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_without_credentials(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient()
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1,))

    assert result.exit_code == 1

    assert u'Unable to locate credentials. Configure credentials by running "aws configure".\n' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_creates_new_revision(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1,))

    assert result.exit_code == 0

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Successfully created revision: 2" in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1,))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_with_role_arn(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-r', 'arn:new:role'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed role_arn to: "arn:new:role" (was: "arn:test:role:1")' in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_new_tag(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-t', 'latest'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert "Updating task definition" in result.output
    assert 'Changed image of container "webserver" to: "webserver:latest" (was: "webserver:123")' in result.output
    assert 'Changed image of container "application" to: "application:latest" (was: "application:123")' in result.output
    assert 'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_one_new_image(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-i', 'application', 'application:latest'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert "Updating task definition" in result.output
    assert 'Changed image of container "application" to: "application:latest" (was: "application:123")' in result.output
    assert 'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_two_new_images(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        update.update,
        (TASK_DEFINITION_ARN_1, '-i', 'application', 'application:latest', '-i', 'webserver', 'webserver:latest')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert "Updating task definition" in result.output
    assert 'Changed image of container "webserver" to: "webserver:latest" (was: "webserver:123")' in result.output
    assert 'Changed image of container "application" to: "application:latest" (was: "application:123")' in result.output
    assert 'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_one_new_command(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-c', 'application', 'foobar'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed command of container "application" to: "foobar" (was: "run")' in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_one_new_environment_variable(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        update.update, (TASK_DEFINITION_ARN_1, '-e', 'application', 'foo', 'bar', '-e', 'webserver', 'foo', 'baz')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "foo" of container "application" to: "bar"' in result.output
    assert u'Changed environment "foo" of container "webserver" to: "baz"' in result.output
    assert u'Changed environment "lorem" of container "webserver" to: "ipsum"' not in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_change_environment_variable_empty_string(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-e', 'application', 'foo', ''))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "foo" of container "application" to: ""' in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_new_empty_environment_variable(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-e', 'application', 'new', ''))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "new" of container "application" to: ""' in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_empty_environment_variable_again(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-e', 'webserver', 'empty', ''))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed environment' not in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_previously_empty_environment_variable_with_value(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-e', 'webserver', 'empty', 'not-empty'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "empty" of container "webserver" to: "not-empty"' in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_exclusive_environment(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        update.update, (TASK_DEFINITION_ARN_1, '-e', 'webserver', 'new-env', 'new-value', '--exclusive-env')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed environment "new-env" of container "webserver" to: "new-value"' in result.output

    assert u'Removed environment "foo" of container "webserver"' in result.output
    assert u'Removed environment "lorem" of container "webserver"' in result.output

    assert u'Removed secret' not in result.output

    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_exclusive_secret(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        update.update, (TASK_DEFINITION_ARN_1, '-s', 'webserver', 'new-secret', 'new-place', '--exclusive-secrets')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed secret "new-secret" of container "webserver" to: "new-place"' in result.output

    assert u'Removed secret "baz" of container "webserver"' in result.output
    assert u'Removed secret "dolor" of container "webserver"' in result.output

    assert u'Removed environment' not in result.output

    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_one_new_secret_variable(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        update.update, (TASK_DEFINITION_ARN_1, '-s', 'application', 'baz', 'qux', '-s', 'webserver', 'baz', 'quux')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" in result.output
    assert u'Changed secret "baz" of container "application" to: "qux"' in result.output
    assert u'Changed secret "baz" of container "webserver" to: "quux"' in result.output
    assert u'Changed secret "dolor" of container "webserver" to: "sit"' not in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_without_changing_environment_value(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-e', 'webserver', 'foo', 'bar'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed environment' not in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_without_changing_secrets_value(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(update.update, (TASK_DEFINITION_ARN_1, '-s', 'webserver', 'baz', 'qux'))

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed secrets' not in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.update.get_ecs_client')
def test_update_task_without_diff(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        update.update, (TASK_DEFINITION_ARN_1, '-t', 'latest', '-e', 'webserver', 'foo', 'barz', '--no-diff')
    )

    assert result.exit_code == 0
    assert not result.exception

    assert f"Update task definition [task={TASK_DEFINITION_ARN_1}]" in result.output
    assert u"Updating task definition" not in result.output
    assert u'Changed environment' not in result.output
    assert u'Successfully created revision: 2' in result.output


@patch('aws_deploy.ecs.commands.cron.get_ecs_client')
def test_cron_without_credentials(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient()
    result = runner.invoke(cron.cron, (CLUSTER_NAME, TASK_DEFINITION_FAMILY_1, 'rule'))

    assert result.exit_code == 1

    assert u'Unable to locate credentials. Configure credentials by running "aws configure".\n' in result.output


@patch('aws_deploy.ecs.commands.cron.get_ecs_client')
def test_cron(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(cron.cron, (CLUSTER_NAME, TASK_DEFINITION_FAMILY_1, 'rule'))

    assert not result.exception
    assert result.exit_code == 0

    assert f'Update task definition [cluster={CLUSTER_NAME}, task={TASK_DEFINITION_FAMILY_1}, rule=rule]' \
           in result.output
    assert u'Creating new task definition revision' in result.output
    assert u'Successfully created revision: 2' in result.output
    assert u'Updating scheduled task' in result.output
    assert u'Deregister task definition revision' in result.output
    assert u'Successfully deregistered revision: 2' in result.output


@patch('aws_deploy.ecs.commands.diff.get_ecs_client')
def test_diff(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient('access_key', 'secret_key')
    result = runner.invoke(
        diff.diff, (TASK_DEFINITION_FAMILY_1, str(TASK_DEFINITION_REVISION_1), str(TASK_DEFINITION_REVISION_3))
    )

    assert not result.exception
    assert result.exit_code == 0

    assert 'change: containers.webserver.image' in result.output
    assert '- "webserver:123"' in result.output
    assert '+ "webserver:456"' in result.output
    assert 'change: containers.webserver.command' in result.output
    assert '- "run"' in result.output
    assert '+ "execute"' in result.output
    assert 'change: containers.webserver.environment.foo' in result.output
    assert '- "bar"' in result.output
    assert '+ "foobar"' in result.output
    assert 'remove: containers.webserver.environment' in result.output
    assert '- empty: ' in result.output
    assert 'change: containers.webserver.secrets.baz' in result.output
    assert '- "qux"' in result.output
    assert '+ "foobaz"' in result.output
    assert 'change: containers.webserver.secrets.dolor' in result.output
    assert '- "sit"' in result.output
    assert '+ "loremdolor"' in result.output
    assert 'change: role_arn' in result.output
    assert '- "arn:test:role:1"' in result.output
    assert '+ "arn:test:another-role:1"' in result.output
    assert 'change: execution_role_arn' in result.output
    assert '- "arn:test:role:1"' in result.output
    assert '+ "arn:test:another-role:1"' in result.output
    assert 'add: containers.webserver.environment' in result.output
    assert '+ newvar: "new value"' in result.output


@patch('aws_deploy.ecs.commands.diff.get_ecs_client')
def test_diff_without_credentials(get_ecs_client, runner):
    get_ecs_client.return_value = EcsTestClient()
    result = runner.invoke(
        diff.diff, (TASK_DEFINITION_FAMILY_1, str(TASK_DEFINITION_REVISION_1), str(TASK_DEFINITION_REVISION_3))
    )

    assert result.exit_code == 1

    assert u'Unable to locate credentials. Configure credentials by running "aws configure".\n' in result.output
