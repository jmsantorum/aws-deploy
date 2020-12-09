from copy import deepcopy
from datetime import datetime

from dateutil.tz import tzlocal

CLUSTER_NAME = u'test-cluster'
CLUSTER_ARN = u'arn:aws:ecs:eu-central-1:123456789012:cluster/%s' % CLUSTER_NAME
SERVICE_NAME = u'test-service'
SERVICE_ARN = u'ecs-svc/12345678901234567890'
DESIRED_COUNT = 2
TASK_DEFINITION_FAMILY_1 = u'test-task'
TASK_DEFINITION_REVISION_1 = 1
TASK_DEFINITION_ROLE_ARN_1 = u'arn:test:role:1'
TASK_DEFINITION_ARN_1 = u'arn:aws:ecs:eu-central-1:123456789012:task-definition/%s:%s' % (TASK_DEFINITION_FAMILY_1,
                                                                                          TASK_DEFINITION_REVISION_1)
TASK_DEFINITION_VOLUMES_1 = []
TASK_DEFINITION_CONTAINERS_1 = [
    {u'name': u'webserver', u'image': u'webserver:123', u'command': u'run',
     u'environment': (
         {"name": "foo", "value": "bar"}, {"name": "lorem", "value": "ipsum"}, {"name": "empty", "value": ""}),
     u'secrets': ({"name": "baz", "valueFrom": "qux"}, {"name": "dolor", "valueFrom": "sit"})},
    {u'name': u'application', u'image': u'application:123', u'command': u'run', u'environment': ()}
]

TASK_DEFINITION_FAMILY_2 = u'test-task'
TASK_DEFINITION_REVISION_2 = 2
TASK_DEFINITION_ARN_2 = u'arn:aws:ecs:eu-central-1:123456789012:task-definition/%s:%s' % (TASK_DEFINITION_FAMILY_2,
                                                                                          TASK_DEFINITION_REVISION_2)
TASK_DEFINITION_VOLUMES_2 = []
TASK_DEFINITION_CONTAINERS_2 = [
    {u'name': u'webserver', u'image': u'webserver:123', u'command': u'run',
     u'environment': (
         {"name": "foo", "value": "bar"}, {"name": "lorem", "value": "ipsum"}, {"name": "empty", "value": ""}),
     u'secrets': ({"name": "baz", "valueFrom": "qux"}, {"name": "dolor", "valueFrom": "sit"})},
    {u'name': u'application', u'image': u'application:123', u'command': u'run', u'environment': ()}
]

TASK_DEFINITION_REVISION_3 = 3
TASK_DEFINITION_ARN_3 = u'arn:aws:ecs:eu-central-1:123456789012:task-definition/%s:%s' % (TASK_DEFINITION_FAMILY_1,
                                                                                          TASK_DEFINITION_REVISION_3)
TASK_DEFINITION_VOLUMES_3 = []
TASK_DEFINITION_CONTAINERS_3 = [
    {u'name': u'webserver', u'image': u'webserver:456', u'command': u'execute',
     u'environment': ({"name": "foo", "value": "foobar"}, {"name": "newvar", "value": "new value"}),
     u'secrets': ({"name": "baz", "valueFrom": "foobaz"}, {"name": "dolor", "valueFrom": "loremdolor"})},
    {u'name': u'application', u'image': u'application:123', u'command': u'run', u'environment': ()}
]
TASK_DEFINITION_ROLE_ARN_3 = u'arn:test:another-role:1'

PAYLOAD_TASK_DEFINITION_1 = {
    u'taskDefinitionArn': TASK_DEFINITION_ARN_1,
    u'family': TASK_DEFINITION_FAMILY_1,
    u'revision': TASK_DEFINITION_REVISION_1,
    u'taskRoleArn': TASK_DEFINITION_ROLE_ARN_1,
    u'executionRoleArn': TASK_DEFINITION_ROLE_ARN_1,
    u'volumes': deepcopy(TASK_DEFINITION_VOLUMES_1),
    u'containerDefinitions': deepcopy(TASK_DEFINITION_CONTAINERS_1),
    u'status': u'active',
    u'requiresAttributes': {},
    u'networkMode': u'host',
    u'placementConstraints': {},
    u'unknownProperty': u'lorem-ipsum',
    u'compatibilities': [u'EC2'],
}

PAYLOAD_TASK_DEFINITION_2 = {
    u'taskDefinitionArn': TASK_DEFINITION_ARN_2,
    u'family': TASK_DEFINITION_FAMILY_2,
    u'revision': TASK_DEFINITION_REVISION_2,
    u'volumes': deepcopy(TASK_DEFINITION_VOLUMES_2),
    u'containerDefinitions': deepcopy(TASK_DEFINITION_CONTAINERS_2),
    u'status': u'active',
    u'unknownProperty': u'lorem-ipsum',
    u'compatibilities': [u'EC2'],
}

PAYLOAD_TASK_DEFINITION_3 = {
    u'taskDefinitionArn': TASK_DEFINITION_ARN_3,
    u'family': TASK_DEFINITION_FAMILY_1,
    u'revision': TASK_DEFINITION_REVISION_3,
    u'taskRoleArn': TASK_DEFINITION_ROLE_ARN_3,
    u'executionRoleArn': TASK_DEFINITION_ROLE_ARN_3,
    u'volumes': deepcopy(TASK_DEFINITION_VOLUMES_3),
    u'containerDefinitions': deepcopy(TASK_DEFINITION_CONTAINERS_3),
    u'status': u'active',
    u'requiresAttributes': {},
    u'networkMode': u'host',
    u'placementConstraints': {},
    u'unknownProperty': u'lorem-ipsum',
    u'compatibilities': [u'EC2'],
}

TASK_ARN_1 = u'arn:aws:ecs:eu-central-1:123456789012:task/12345678-1234-1234-1234-123456789011'
TASK_ARN_2 = u'arn:aws:ecs:eu-central-1:123456789012:task/12345678-1234-1234-1234-123456789012'

PAYLOAD_TASK_1 = {
    u'taskArn': TASK_ARN_1,
    u'clusterArn': CLUSTER_ARN,
    u'taskDefinitionArn': TASK_DEFINITION_ARN_1,
    u'containerInstanceArn': u'arn:aws:ecs:eu-central-1:123456789012:container-instance/12345678-123456-123456-123456',
    u'overrides': {u'containerOverrides': []},
    u'lastStatus': u'RUNNING',
    u'desiredStatus': u'RUNNING',
    u'containers': TASK_DEFINITION_CONTAINERS_1,
    u'startedBy': SERVICE_ARN
}

PAYLOAD_TASK_2 = {
    u'taskArn': TASK_ARN_2,
    u'clusterArn': CLUSTER_ARN,
    u'taskDefinitionArn': TASK_DEFINITION_ARN_1,
    u'containerInstanceArn': u'arn:aws:ecs:eu-central-1:123456789012:container-instance/12345678-123456-123456-123456',
    u'overrides': {u'containerOverrides': []},
    u'lastStatus': u'RUNNING',
    u'desiredStatus': u'RUNNING',
    u'containers': TASK_DEFINITION_CONTAINERS_1,
    u'startedBy': SERVICE_ARN
}

PAYLOAD_DEPLOYMENTS = [
    {
        u'status': u'PRIMARY',
        u'pendingCount': 0,
        u'desiredCount': DESIRED_COUNT,
        u'runningCount': DESIRED_COUNT,
        u'taskDefinition': TASK_DEFINITION_ARN_1,
        u'createdAt': datetime(2016, 3, 11, 12, 0, 0, 000000, tzinfo=tzlocal()),
        u'updatedAt': datetime(2016, 3, 11, 12, 5, 0, 000000, tzinfo=tzlocal()),
        u'id': u'ecs-svc/0000000000000000002',
    }
]

PAYLOAD_EVENTS = [
    {
        u'id': u'error',
        u'createdAt': datetime.now(tz=tzlocal()),
        u'message': u'Service was unable to Lorem Ipsum'
    },
    {
        u'id': u'older_error',
        u'createdAt': datetime(2016, 3, 11, 12, 0, 10, 000000, tzinfo=tzlocal()),
        u'message': u'Service was unable to Lorem Ipsum'
    }
]

PAYLOAD_SERVICE = {
    u'serviceName': SERVICE_NAME,
    u'desiredCount': DESIRED_COUNT,
    u'taskDefinition': TASK_DEFINITION_ARN_1,
    u'deployments': PAYLOAD_DEPLOYMENTS,
    u'events': []
}

PAYLOAD_SERVICE_WITH_ERRORS = {
    u'serviceName': SERVICE_NAME,
    u'desiredCount': DESIRED_COUNT,
    u'taskDefinition': TASK_DEFINITION_ARN_1,
    u'deployments': PAYLOAD_DEPLOYMENTS,
    u'events': PAYLOAD_EVENTS
}

PAYLOAD_SERVICE_WITHOUT_DEPLOYMENTS = {
    u'serviceName': SERVICE_NAME,
    u'desiredCount': DESIRED_COUNT,
    u'taskDefinition': TASK_DEFINITION_ARN_1,
    u'deployments': [],
    u'events': []
}

RESPONSE_SERVICE = {
    u"service": PAYLOAD_SERVICE
}

RESPONSE_SERVICE_WITH_ERRORS = {
    u"service": PAYLOAD_SERVICE_WITH_ERRORS
}

RESPONSE_DESCRIBE_SERVICES = {
    u"services": [PAYLOAD_SERVICE]
}

RESPONSE_TASK_DEFINITION = {
    u"taskDefinition": PAYLOAD_TASK_DEFINITION_1
}

RESPONSE_TASK_DEFINITION_2 = {
    u"taskDefinition": PAYLOAD_TASK_DEFINITION_2
}

RESPONSE_TASK_DEFINITION_3 = {
    u"taskDefinition": PAYLOAD_TASK_DEFINITION_3
}

RESPONSE_TASK_DEFINITIONS = {
    TASK_DEFINITION_ARN_1: RESPONSE_TASK_DEFINITION,
    TASK_DEFINITION_ARN_2: RESPONSE_TASK_DEFINITION_2,
    TASK_DEFINITION_ARN_3: RESPONSE_TASK_DEFINITION_3,
    u'test-task:1': RESPONSE_TASK_DEFINITION,
    u'test-task:2': RESPONSE_TASK_DEFINITION_2,
    u'test-task:3': RESPONSE_TASK_DEFINITION_3,
    u'test-task': RESPONSE_TASK_DEFINITION_2,
}

RESPONSE_LIST_TASKS_2 = {
    u"taskArns": [TASK_ARN_1, TASK_ARN_2]
}

RESPONSE_LIST_TASKS_1 = {
    u"taskArns": [TASK_ARN_1]
}

RESPONSE_LIST_TASKS_0 = {
    u"taskArns": []
}

RESPONSE_DESCRIBE_TASKS = {
    u"tasks": [PAYLOAD_TASK_1, PAYLOAD_TASK_2]
}
