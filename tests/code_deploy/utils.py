from copy import deepcopy
from datetime import datetime, timedelta

from botocore.exceptions import ClientError

from aws_deploy.code_deploy.helper import (
    UnknownTaskDefinitionError, CodeDeployConnectionError, CodeDeployDeployment, CodeDeployApplication,
    CodeDeployDeploymentGroup, CodeDeployApplicationRevision, CodeDeployRevision
)
from aws_deploy.ecs.helper import EcsTaskDefinition

APPLICATION_ID = 'a5143954-0b4e-4336-866f-bf1f52b183d3'
APPLICATION_NAME = 'test-application'
DEPLOYMENT_GROUP_NAME = 'test-deployment-group'
REVISION_TYPE = 'AppSpecContent'
DEPLOYMENT_ID = 'd-ABC123DEF'

APPLICATION_PAYLOAD = {
    'application': {
        'applicationId': APPLICATION_ID,
        'applicationName': APPLICATION_NAME,
        'createTime': datetime(2020, 1, 1, 1, 0),
        'linkedToGitHub': False,
        'computePlatform': 'ECS'
    }
}

DEPLOYMENT_GROUP_PAYLOAD = {
    'deploymentGroupInfo': {
        'applicationName': APPLICATION_NAME,
        'deploymentGroupId': '112bc71b-86a5-481d-a9b4-6870019928f1',
        'deploymentGroupName': DEPLOYMENT_GROUP_NAME,
        'deploymentConfigName': 'CodeDeployDefault.ECSAllAtOnce',
        'ec2TagFilters': [],
        'onPremisesInstanceTagFilters': [],
        'autoScalingGroups': [],
        'serviceRoleArn': 'arn:aws:iam::123456789012:role/code_deploy_service_role',
        'targetRevision': {
            'revisionType': 'AppSpecContent',
            'appSpecContent': {'sha256': 'ca50d13af7bc8d4ea4f6600dfd82e38b41a0a14bd5edf242464eb025895f0bc9'}
        },
        'triggerConfigurations': [],
        'autoRollbackConfiguration': {'enabled': True, 'events': ['DEPLOYMENT_FAILURE']},
        'deploymentStyle': {
            'deploymentType': 'BLUE_GREEN',
            'deploymentOption': 'WITH_TRAFFIC_CONTROL'
        },
        'blueGreenDeploymentConfiguration': {
            'terminateBlueInstancesOnDeploymentSuccess': {
                'action': 'TERMINATE',
                'terminationWaitTimeInMinutes': 1
            },
            'deploymentReadyOption': {
                'actionOnTimeout': 'CONTINUE_DEPLOYMENT',
                'waitTimeInMinutes': 0
            }
        },
        'loadBalancerInfo': {
            'targetGroupPairInfoList': [
                {
                    'targetGroups': [
                        {'name': 'blue-green-tg-one'}, {'name': 'blue-green-tg-two'}
                    ],
                    'prodTrafficRoute': {
                        'listenerArns': [
                            'arn:aws:elasticloadbalancing:eu-west-1:123456789012:listener/app/test-app/12345678'
                        ]
                    }
                }
            ]
        },
        'lastSuccessfulDeployment': {
            'deploymentId': DEPLOYMENT_ID,
            'status': 'Succeeded',
            'endTime': datetime(2020, 1, 1, 1, 1),
            'createTime': datetime(2020, 1, 1, 1, 0)
        },
        'lastAttemptedDeployment': {
            'deploymentId': DEPLOYMENT_ID,
            'status': 'Succeeded',
            'endTime': datetime(2020, 1, 1, 1, 1),
            'createTime': datetime(2020, 1, 1, 1, 0)
        },
        'computePlatform': 'ECS',
        'ecsServices': [{'serviceName': 'test-service', 'clusterName': 'test-cluster'}]
    }
}

DEPLOYMENT_GROUP_PAYLOAD_2 = {
    'deploymentGroupInfo': {
        'applicationName': APPLICATION_NAME,
        'deploymentGroupId': '112bc71b-86a5-481d-a9b4-6870019928f1',
        'deploymentGroupName': DEPLOYMENT_GROUP_NAME,
        'deploymentConfigName': 'CodeDeployDefault.ECSAllAtOnce',
        'ec2TagFilters': [],
        'onPremisesInstanceTagFilters': [],
        'autoScalingGroups': [],
        'serviceRoleArn': 'arn:aws:iam::123456789012:role/code_deploy_service_role',
        'targetRevision': {
            'revisionType': 'String',
            'string': {'sha256': 'ca50d13af7bc8d4ea4f6600dfd82e38b41a0a14bd5edf242464eb025895f0bc9'}
        },
        'triggerConfigurations': [],
        'autoRollbackConfiguration': {'enabled': True, 'events': ['DEPLOYMENT_FAILURE']},
        'deploymentStyle': {
            'deploymentType': 'BLUE_GREEN',
            'deploymentOption': 'WITH_TRAFFIC_CONTROL'
        },
        'blueGreenDeploymentConfiguration': {
            'terminateBlueInstancesOnDeploymentSuccess': {
                'action': 'TERMINATE',
                'terminationWaitTimeInMinutes': 1
            },
            'deploymentReadyOption': {
                'actionOnTimeout': 'CONTINUE_DEPLOYMENT',
                'waitTimeInMinutes': 0
            }
        },
        'loadBalancerInfo': {
            'targetGroupPairInfoList': [
                {
                    'targetGroups': [
                        {'name': 'blue-green-tg-one'}, {'name': 'blue-green-tg-two'}
                    ],
                    'prodTrafficRoute': {
                        'listenerArns': [
                            'arn:aws:elasticloadbalancing:eu-west-1:123456789012:listener/app/test-app/12345678'
                        ]
                    }
                }
            ]
        },
        'lastSuccessfulDeployment': {
            'deploymentId': DEPLOYMENT_ID,
            'status': 'Succeeded',
            'endTime': datetime(2020, 1, 1, 1, 1),
            'createTime': datetime(2020, 1, 1, 1, 0)
        },
        'lastAttemptedDeployment': {
            'deploymentId': DEPLOYMENT_ID,
            'status': 'Succeeded',
            'endTime': datetime(2020, 1, 1, 1, 1),
            'createTime': datetime(2020, 1, 1, 1, 0)
        },
        'computePlatform': 'ECS',
        'ecsServices': [{'serviceName': 'test-service', 'clusterName': 'test-cluster'}]
    }
}

APPLICATION_REVISION_PAYLOAD = {
    'applicationName': APPLICATION_NAME,
    'revision': {
        'revisionType': REVISION_TYPE,
        'appSpecContent': {
            'content': '{"version":0.0,"Resources":[{"TargetService":{"Type":"AWS::ECS::Service","Properties":{"TaskDefinition":"arn:aws:ecs:eu-west-1:123456789012:task-definition/test-task:1","LoadBalancerInfo":{"ContainerName":"container-name","ContainerPort":8080}}}}]}',  # noqa: E501
            'sha256': 'ca50d13af7bc8d4ea4f6600dfd82e38b41a0a14bd5edf242464eb025895f0bc9'
        }
    },
    'revisionInfo': {
        'description': 'Application revision registered by Deployment ID: d-ABC123DEF',
        'deploymentGroups': [DEPLOYMENT_GROUP_NAME],
        'firstUsedTime': datetime(2020, 1, 1, 1, 0),
        'lastUsedTime': datetime(2020, 1, 1, 1, 0),
        'registerTime': datetime(2020, 1, 1, 1, 0)
    }
}

TASK_DEFINITION_PAYLOAD = {
    'taskDefinition': {
        'taskDefinitionArn': 'arn:aws:ecs:eu-west-1:123456789012:task-definition/test-task-1',
        'containerDefinitions': [
            {
                'name': 'container-name',
                'image': 'application:123456',
                'cpu': 0,
                'memory': 1024,
                'memoryReservation': 256,
                'portMappings': [{'containerPort': 8080, 'hostPort': 0, 'protocol': 'tcp'}],
                'essential': True,
                'environment': [],
                'mountPoints': [],
                'volumesFrom': [],
                'secrets': [],
                'logConfiguration': {}
            }
        ],
        'family': 'test-task',
        'executionRoleArn': 'arn:aws:iam::123456789012:role/execution_role',
        'networkMode': 'bridge',
        'revision': 1,
        'volumes': [],
        'status': 'ACTIVE',
        'requiresAttributes': [],
        'placementConstraints': [],
        'compatibilities': ['EC2'],
        'requiresCompatibilities': ['EC2']
    },
    'tags': []
}

DEPLOYMENT_PAYLOAD = {
    'deploymentInfo': {
        'applicationName': APPLICATION_NAME,
        'deploymentGroupName': DEPLOYMENT_GROUP_NAME,
        'deploymentConfigName': 'CodeDeployDefault.ECSAllAtOnce',
        'deploymentId': DEPLOYMENT_ID,
        'previousRevision': {
            'revisionType': REVISION_TYPE,
            'appSpecContent': {'sha256': 'ca50d13af7bc8d4ea4f6600dfd82e38b41a0a14bd5edf242464eb025895f0bc9'}},
        'revision': {
            'revisionType': 'AppSpecContent',
            'appSpecContent': {'sha256': 'ca50d13af7bc8d4ea4f6600dfd82e38b41a0a14bd5edf242464eb025895f0bc9'}},
        'status': '[status]',
        'createTime': datetime(2020, 1, 1, 1, 0),
        'completeTime': datetime(2020, 1, 1, 1, 1),
        'deploymentOverview': {
            'Pending': 0, 'InProgress': 0, 'Succeeded': 1, 'Failed': 0, 'Skipped': 0, 'Ready': 0
        },
        'creator': 'user',
        'ignoreApplicationStopFailures': False,
        'autoRollbackConfiguration': {'enabled': True, 'events': ['DEPLOYMENT_FAILURE']},
        'updateOutdatedInstancesOnly': False,
        'deploymentStyle': {'deploymentType': 'BLUE_GREEN', 'deploymentOption': 'WITH_TRAFFIC_CONTROL'},
        'instanceTerminationWaitTimeStarted': True,
        'blueGreenDeploymentConfiguration': {
            'terminateBlueInstancesOnDeploymentSuccess': {
                'action': 'TERMINATE', 'terminationWaitTimeInMinutes': 1
            },
            'deploymentReadyOption': {'actionOnTimeout': 'CONTINUE_DEPLOYMENT', 'waitTimeInMinutes': 0}
        },
        'loadBalancerInfo': {
            'targetGroupPairInfoList': [
                {
                    'targetGroups': [{'name': 'blue-green-tg-one'}, {'name': 'blue-green-tg-two'}],
                    'prodTrafficRoute': {
                        'listenerArns': [
                            'arn:aws:elasticloadbalancing:eu-west-1:123456789012:listener/app/test-app/12345678'
                        ]
                    }
                }
            ]
        },
        'fileExistsBehavior': 'DISALLOW',
        'deploymentStatusMessages': [],
        'computePlatform': 'ECS'
    }
}


class CodeDeployTestClient:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name=None,
                 profile_name=None, deployment_errors=False, client_errors=False, wait=0):
        self.access_key_id = aws_access_key_id
        self.secret_access_key = aws_secret_access_key
        self.region = region_name
        self.profile = profile_name
        self.deployment_errors = deployment_errors
        self.client_errors = client_errors
        self.wait_until = datetime.now() + timedelta(seconds=wait)

    def get_application(self, application_name: str) -> CodeDeployApplication:
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        if application_name != APPLICATION_NAME:
            error_response = {
                'Error': {
                    'Code': 'ApplicationDoesNotExistException',
                    'Message': f'No application found for name: {application_name}'
                }
            }
            raise ClientError(error_response, 'GetApplication')

        application_payload = APPLICATION_PAYLOAD

        return CodeDeployApplication(
            **application_payload['application']
        )

    def get_deployment_group(self, application_name: str, deployment_group_name: str) -> CodeDeployDeploymentGroup:
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        if application_name != APPLICATION_NAME:
            error_response = {
                'Error': {
                    'Code': 'ApplicationDoesNotExistException',
                    'Message': f'No application found for name: {application_name}'
                }
            }
            raise ClientError(error_response, 'GetDeploymentGroup')

        if deployment_group_name != DEPLOYMENT_GROUP_NAME:
            error_response = {
                'Error': {
                    'Code': 'DeploymentGroupDoesNotExistException',
                    'Message': f'No Deployment Group found for name: {deployment_group_name}'
                }
            }
            raise ClientError(error_response, 'GetDeploymentGroup')

        deployment_group_payload = DEPLOYMENT_GROUP_PAYLOAD

        return CodeDeployDeploymentGroup(
            **deployment_group_payload['deploymentGroupInfo']
        )

    def get_application_revision(self, application_name: str, deployment_group: CodeDeployDeploymentGroup) -> CodeDeployApplicationRevision:  # noqa E501
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        if application_name != APPLICATION_NAME:
            error_response = {
                'Error': {
                    'Code': 'ApplicationDoesNotExistException',
                    'Message': f'No application found for name: {application_name}'
                }
            }
            raise ClientError(error_response, 'GetApplicationRevision')

        target_revision = deployment_group.target_revision
        revision_type = target_revision['revisionType']
        revision = target_revision['appSpecContent']

        if revision_type not in ['S3', 'GitHub', 'String', 'AppSpecContent']:
            error_response = {
                'Error': {
                    'Code': 'InvalidRevisionException',
                    'Message': f"Invalid revision type '{revision_type}'"
                }
            }
            raise ClientError(error_response, 'GetApplicationRevision')

        if revision['sha256'] != 'ca50d13af7bc8d4ea4f6600dfd82e38b41a0a14bd5edf242464eb025895f0bc9':
            error_response = {
                'Error': {
                    'Code': 'InvalidRevisionException',
                    'Message': 'No application revision found for revision.'
                }
            }
            raise ClientError(error_response, 'GetApplicationRevision')

        application_revision_payload = APPLICATION_REVISION_PAYLOAD

        return CodeDeployApplicationRevision(
            **application_revision_payload
        )

    def get_task_definition(self, task_definition_arn: str):
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        if task_definition_arn != 'arn:aws:ecs:eu-west-1:123456789012:task-definition/test-task:1':
            raise UnknownTaskDefinitionError(
                'An error occurred (ClientException) when calling the DescribeTaskDefinition operation: Unable to describe task definition.')  # noqa: E501

        task_definition_payload = TASK_DEFINITION_PAYLOAD

        return EcsTaskDefinition(
            tags=task_definition_payload.get('tags', None), **task_definition_payload['taskDefinition']
        )

    def create_deployment(self, application_name: str, deployment_group_name: str,
                          revision: CodeDeployRevision) -> CodeDeployDeployment:  # noqa: E501
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        if application_name != APPLICATION_NAME:
            error_response = {
                'Error': {
                    'Code': 'ApplicationDoesNotExistException',
                    'Message': f'No application found for name: {application_name}'
                }
            }
            raise ClientError(error_response, 'CreateDeployment')

        if deployment_group_name != DEPLOYMENT_GROUP_NAME:
            error_response = {
                'Error': {
                    'Code': 'DeploymentGroupDoesNotExistException',
                    'Message': f'No Deployment Group found for name: {deployment_group_name}'
                }
            }
            raise ClientError(error_response, 'CreateDeployment')

        deployment_payload = {
            'deploymentId': DEPLOYMENT_ID
        }

        return CodeDeployDeployment(
            deploymentId=deployment_payload['deploymentId'],
            applicationName=None, deploymentGroupName=None, deploymentConfigName=None, revision=None, status=None
        )

    def get_deployment(self, deployment_id: str):
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        if deployment_id != DEPLOYMENT_ID:
            error_response = {
                'Error': {
                    'Code': 'DeploymentDoesNotExistException',
                    'Message': f'The deployment {deployment_id} could not be found'
                }
            }
            raise ClientError(error_response, 'GetDeployment')

        deployment_payload = DEPLOYMENT_PAYLOAD
        if self.wait_until <= datetime.now():
            deployment_payload['deploymentInfo']['status'] = 'Succeeded'
        else:
            deployment_payload['deploymentInfo']['status'] = 'InProgress'

        return CodeDeployDeployment(
            **deployment_payload['deploymentInfo']
        )

    def register_task_definition(self, task_definition: EcsTaskDefinition):
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')

        return deepcopy(task_definition)

    def deregister_task_definition(self, task_definition_arn):
        if not self.access_key_id or not self.secret_access_key:
            raise CodeDeployConnectionError('Unable to locate credentials')
