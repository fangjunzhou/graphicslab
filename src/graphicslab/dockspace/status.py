from typing import Dict
import copy
from observer.observer import Observable, Observer

StatusType = str | float


class StatusState(Observable):
    status_table: Dict[str, StatusType]

    def __init__(self, name=None):
        super(StatusState, self).__init__(name)
        self.status_table = {}

    def update_status(self, key, status: StatusType = "Working"):
        self.status_table[key] = status
        self.notify(self.status_table)

    def finish_status(self, key):
        if key in self.status_table:
            del self.status_table[key]
        self.notify(self.status_table)


class StatusObserver(Observer):
    _value: Dict[str, StatusType]

    def __init__(self, name=None):
        super(StatusObserver, self).__init__(name)
        self._value = {}

    def update(self, *new_state):
        new_state = new_state[0]
        self._value = copy.deepcopy(new_state)

    @property
    def value(self):
        return self._value
