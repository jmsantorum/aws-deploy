from copy import deepcopy
from datetime import timedelta, datetime

from botocore.exceptions import ClientError, NoCredentialsError

from aws_deploy.ecs.helper import EcsConnectionError, UnknownTaskDefinitionError
from tests.ecs.constants import (
    PAYLOAD_SERVICE_WITH_ERRORS, PAYLOAD_SERVICE, RESPONSE_TASK_DEFINITIONS, RESPONSE_LIST_TASKS_2,
    RESPONSE_LIST_TASKS_0, RESPONSE_DESCRIBE_TASKS, RESPONSE_TASK_DEFINITION_2, RESPONSE_TASK_DEFINITION,
    RESPONSE_SERVICE_WITH_ERRORS, RESPONSE_SERVICE
)


class EcsTestClient(object):
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name=None,
                 profile_name=None, deployment_errors=False, client_errors=False,
                 wait=0):
        super(EcsTestClient, self).__init__()
        self.access_key_id = aws_access_key_id
        self.secret_access_key = aws_secret_access_key
        self.region = region_name
        self.profile = profile_name
        self.deployment_errors = deployment_errors
        self.client_errors = client_errors
        self.wait_until = datetime.now() + timedelta(seconds=wait)

    def describe_services(self, cluster_name, service_name):
        if not self.access_key_id or not self.secret_access_key:
            raise NoCredentialsError()
        if cluster_name != u'test-cluster':
            error_response = {u'Error': {u'Code': u'ClusterNotFoundException', u'Message': u'Cluster not found.'}}
            raise ClientError(error_response, u'DescribeServices')
        if service_name != u'test-service':
            return {u'services': []}
        if self.deployment_errors:
            return {
                u"services": [PAYLOAD_SERVICE_WITH_ERRORS],
                u"failures": []
            }
        return {
            u"services": [PAYLOAD_SERVICE],
            u"failures": []
        }

    def describe_task_definition(self, task_definition_arn):
        if not self.access_key_id or not self.secret_access_key:
            raise EcsConnectionError(u'Unable to locate credentials. Configure credentials by running "aws configure".')
        if task_definition_arn in RESPONSE_TASK_DEFINITIONS:
            return deepcopy(RESPONSE_TASK_DEFINITIONS[task_definition_arn])
        raise UnknownTaskDefinitionError('Unknown task definition arn: %s' % task_definition_arn)

    def list_tasks(self, cluster_name, service_name):
        if self.wait_until <= datetime.now():
            return deepcopy(RESPONSE_LIST_TASKS_2)
        return deepcopy(RESPONSE_LIST_TASKS_0)

    def describe_tasks(self, cluster_name, task_arns):
        return deepcopy(RESPONSE_DESCRIBE_TASKS)

    def register_task_definition(self, family, containers, volumes, role_arn,
                                 execution_role_arn, tags, additional_properties):
        if not self.access_key_id or not self.secret_access_key:
            raise EcsConnectionError(u'Unable to locate credentials. Configure credentials by running "aws configure".')
        return deepcopy(RESPONSE_TASK_DEFINITION_2)

    def deregister_task_definition(self, task_definition_arn):
        return deepcopy(RESPONSE_TASK_DEFINITION)

    def update_service(self, cluster, service, desired_count, task_definition):
        if self.client_errors:
            error = dict(Error=dict(Code=123, Message="Something went wrong"))
            raise ClientError(error, 'fake_error')
        if self.deployment_errors:
            return deepcopy(RESPONSE_SERVICE_WITH_ERRORS)
        return deepcopy(RESPONSE_SERVICE)

    def run_task(self, cluster, task_definition, count, started_by, overrides,
                 launchtype='EC2', subnets=(), security_groups=(),
                 public_ip=False, platform_version=None):
        if not self.access_key_id or not self.secret_access_key:
            raise EcsConnectionError(u'Unable to locate credentials. Configure credentials by running "aws configure".')
        if cluster == 'unknown-cluster':
            raise EcsConnectionError(
                u'An error occurred (ClusterNotFoundException) when calling the RunTask operation: Cluster not found.')
        if self.deployment_errors:
            error = dict(Error=dict(Code=123, Message="Something went wrong"))
            raise ClientError(error, 'fake_error')
        return dict(tasks=[dict(taskArn='arn:foo:bar'), dict(taskArn='arn:lorem:ipsum')])

    def update_rule(self, cluster, rule, task_definition):
        if not self.access_key_id or not self.secret_access_key:
            raise EcsConnectionError(u'Unable to locate credentials. Configure credentials by running "aws configure".')
        if cluster == 'unknown-cluster':
            raise EcsConnectionError(
                u'An error occurred (ClusterNotFoundException) when calling the RunTask operation: Cluster not found.')
