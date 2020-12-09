from abc import ABC, abstractmethod


class Notification(ABC):
    @abstractmethod
    def notify_start(self, cluster, tag, task_definition, comment, user, service=None, rule=None):
        return NotImplemented

    @abstractmethod
    def notify_success(self, cluster, revision, service=None, rule=None):
        return NotImplemented

    @abstractmethod
    def notify_failure(self, cluster, error, service=None, rule=None):
        return NotImplemented
