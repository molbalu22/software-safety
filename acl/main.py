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

    def set_permission_unchecked(self, user, permission):
        if permission not in Resource.PERMISSIONS:
            raise NoSuchPermissionError()

        current_permissions = self.acl.get(user.name)

        if current_permissions is None:
            current_permissions = []

        current_permissions.append(permission)
        self.acl[user.name] = current_permissions


    def get_acl_str(self):
        if len(self.acl.keys()) == 0:
            return "No access granted to resource '{self.name}'"

        acl_str = ""

        for user_name, acl_entry in self.acl.items():
            permission_str = ", ".join(acl_entry)
            return f"{user_name}: {permission_str}"


class State:
    def __init__(self):
        self.users = {}
        self.resources = {}

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


def add_user_command(state, user_name):
    user = User(user_name)
    try:
        state.add_user(user)
    except DuplicateUserError:
        print("User '{user.name}' already exists, try again")


def add_resource_command(state, resource_name):
    resource = Resource(resource_name)
    try:
        state.add_resource(resource)
    except DuplicateResourceError:
        print("Resource '{resource.name}' already exists, try again")


def set_permission_command(state, resource_name, user_name, permission):
    try:
        state.set_permission(resource_name, user_name, permission)
    except NoSuchResourceError:
        print("Resource '{resource_name}' doesn't exist, try again")
    except NoSuchUserError:
        print("User '{user_name}' doesn't exist, try again")
    except NoSuchPermissionError:
        print("Permission '{permission}' is invalid for resource '{resource_name}', try again")


def get_acl_command(state, resource_name):
    try:
        pass
    except NoSuchResourceError:
        print("Resource '{resource_name}' doesn't exist, try again")


class Command:
    pass


class Commands:
    COMMANDS = [
        Command(),
    ]


def usage():
    for command in Commands.COMMANDS:
        pass


def run_next_command(app_state):
    pass


def main():
    app_state = State()

    usage()

    try:
        while True:
            run_next_command(app_state)
    except UserExit:
        return


if __name__ == "__main__":
    main()
