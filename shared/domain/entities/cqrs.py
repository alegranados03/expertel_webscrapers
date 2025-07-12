from abc import ABC, abstractmethod


class Command(ABC):
    @abstractmethod
    def execute(self):
        raise NotImplementedError


class Query(ABC):
    @abstractmethod
    def execute(self):
        raise NotImplementedError
