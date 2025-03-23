import os
import signal
import sys

from abc import ABC, abstractmethod
from inspect import signature


class NoSuchUserError(Exception):
    pass


class NoSuchResourceError(Exception):
    pass


class DuplicateUserError(Exception):
    pass


class DuplicateResourceError(Exception):
    pass


class NoSuchPermissionError(Exception):
    pass


class UserExit(Exception):
    pass


class User:
    def __init__(self, name):
        self.name = name


class Resource:
    PERMISSIONS = ["read", "write", "append", "execute", "own"]

    def __init__(self, name):
        self.name = name
        self.acl = {}

    # 'Unchecked' means the user is assumed to exist, ensure that before calling
    def set_permission_unchecked(self, user, permission):
        if permission not in Resource.PERMISSIONS:
            raise NoSuchPermissionError()

        current_permissions = self.acl.get(user.name)

        if current_permissions is None:
            current_permissions = []

        current_permissions.append(permission)

        self.acl[user.name] = sorted(
            set(current_permissions),
            key=Resource.PERMISSIONS.index
        )

    # 'Unchecked' means the user is assumed to exist, ensure that before calling
    def check_permission_unchecked(self, user, permission):
        if permission not in Resource.PERMISSIONS:
            raise NoSuchPermissionError()

        acl_entry = self.acl.get(user.name)

        return (
            acl_entry is not None
            and permission in acl_entry
        )

    def get_acl_str(self):
        if len(self.acl.keys()) == 0:
            return f"No access granted to resource '{self.name}'."

        acl_entries = []

        for user_name, acl_entry in self.acl.items():
            permission_str = ", ".join(acl_entry)
            acl_entries.append(f"{user_name}: {permission_str}")

        return "\n".join(acl_entries)


class Command(ABC):
    def __init__(self, command_prefix: list[str]):
        self.command_prefix = command_prefix
        self.params = Command.inspect_params(self.execute)
        self.param_names = list(param_name for param_name, *_ in self.params)

    @staticmethod
    def inspect_params(method):
        raw_params = signature(method).parameters
        params = []

        for _, param in raw_params.items():
            if param.name == "state":
                continue

            params.append((param.name, param.annotation))

        return params

    @abstractmethod
    def execute(self, state, *params):
        pass


class AddUserCommand(Command):
    def execute(self, state, user_name: str):
        user = User(user_name)

        try:
            state.add_user(user)
        except DuplicateUserError:
            print(f"User '{user.name}' already exists. Try again.")


class AddResourceCommand(Command):
    def execute(self, state, resource_name: str):
        resource = Resource(resource_name)

        try:
            state.add_resource(resource)
        except DuplicateResourceError:
            print(f"Resource '{resource.name}' already exists. Try again.")


class SetPermissionCommand(Command):
    def execute(self, state, resource_name: str, user_name: str, permission: str):
        try:
            state.set_permission(resource_name, user_name, permission)
        except NoSuchResourceError:
            print(f"Resource '{resource_name}' doesn't exist. Try again.")
        except NoSuchUserError:
            print(f"User '{user_name}' doesn't exist. Try again.")
        except NoSuchPermissionError:
            print(f"Permission '{permission}' is invalid for resource '{resource_name}'. Try again.")


class CheckPermissionCommand(Command):
    def execute(self, state, resource_name: str, user_name: str, permission: str):
        try:
            is_allowed = state.check_permission(resource_name, user_name, permission)
            print(is_allowed)
            print("Access granted." if is_allowed else "Permission denied.")
        except NoSuchResourceError:
            print(f"Resource '{resource_name}' doesn't exist. Try again.")
        except NoSuchUserError:
            print(f"User '{user_name}' doesn't exist. Try again.")
        except NoSuchPermissionError:
            print(f"Permission '{permission}' is invalid for resource '{resource_name}'. Try again.")


class GetAclCommand(Command):
    def execute(self, state, resource_name: str):
        try:
            print(f"ACL of '{resource_name}':")
            print(state.get_acl(resource_name))
        except NoSuchResourceError:
            print(f"Resource '{resource_name}' doesn't exist. Try again.")


class AppState:
    def __init__(self, *, commands: list[Command], DEBUG=False):
        self.commands = commands

        self.help = False
        self.first_prompt = True

        self.DEBUG = DEBUG

        self.users: dict[str, User] = {}
        self.resources: dict[str, Resource] = {}

    def add_user(self, user):
        if user.name in self.users:
            raise DuplicateUserError()

        self.users[user.name] = user

    def add_resource(self, resource):
        if resource.name in self.resources:
            raise DuplicateResourceError()

        self.resources[resource.name] = resource

    def set_permission(self, resource_name, user_name, permission):
        if not resource_name in self.resources:
            raise NoSuchResourceError()

        if not user_name in self.users:
            raise NoSuchUserError()

        resource = self.resources[resource_name]
        user = self.users[user_name]

        resource.set_permission_unchecked(user, permission)


    def check_permission(self, resource_name, user_name, permission):
        if not resource_name in self.resources:
            raise NoSuchResourceError()

        if not user_name in self.users:
            raise NoSuchUserError()

        resource = self.resources[resource_name]
        user = self.users[user_name]

        return resource.check_permission_unchecked(user, permission)


    def get_acl(self, resource_name):
        if not resource_name in self.resources:
            raise NoSuchResourceError()

        resource = self.resources[resource_name]
        return resource.get_acl_str()


def print_command_usage(command):
    print(" ".join(command.command_prefix), end=" ")
    print(" ".join(map(str.upper, command.param_names)))


def print_usage(app_state: AppState):
    print("Available commands:")
    print()

    print("help  ->  Display this help message.")
    print("exit  ->  Exit the program. All entered data will be lost.")
    print()

    for command in app_state.commands:
        print_command_usage(command)


def print_help(app_state: AppState):
    if app_state.first_prompt or app_state.help:
        app_state.first_prompt = False
        app_state.help = False
        print()
        print_usage(app_state)
        print()


def run_next_command(app_state: AppState):
    tokens = input("? ").split()

    if app_state.DEBUG:
        print(tokens)

    if len(tokens) == 1:
        if tokens[0] == "help":
            app_state.help = True
            return
        if tokens[0] == "exit":
            raise UserExit

    for command in app_state.commands:
        input_prefix = tokens[:len(command.command_prefix)]

        if input_prefix == command.command_prefix:
            if app_state.DEBUG:
                print(f"Command '{type(command)}' matched.")

            input_params = tokens[len(command.command_prefix):]

            if len(input_params) != len(command.params):
                print("Invalid parameters.")
                print("Usage:")
                print_command_usage(command)
                return

            if app_state.DEBUG:
                print(f"Calling the command with params {input_params}.")

            command.execute(app_state, *input_params)
            return

    print("Invalid command. Try again.")


def main():
    app_state = AppState(
        commands=[
            AddUserCommand(["add", "user"]),
            AddResourceCommand(["add", "resource"]),
            SetPermissionCommand(["set", "permission"]),
            CheckPermissionCommand(["check", "permission"]),
            GetAclCommand(["get", "acl"]),
        ],
        # DEBUG=True,
    )

    try:
        while True:
            print_help(app_state)
            run_next_command(app_state)
    except UserExit:
        return


def exit_on_signal(*_):
    print()
    EX_OK = getattr(os, "EX_OK", 0)
    sys.exit(EX_OK)


if __name__ == "__main__":
    # Make sure ^C is handled gracefully
    signal.signal(signal.SIGINT, exit_on_signal)

    try:
        main()
    # Make sure ^C is handled gracefully
    except KeyboardInterrupt:
        print()
