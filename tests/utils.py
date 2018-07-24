from typing import Any, Dict

from wrench.models import Group, User
from wrench.resources import Resource
from wrench.translators.foreign import to_foreign_group


def to_foreign_user_response(user: User) -> Dict[str, Any]:
    return {
        'id': user.id,
        'gpgkey': {'id': user.gpg_key.id, 'fingerprint': user.gpg_key.fingerprint,
                   'armored_key': user.gpg_key.armored_key},
        'groups_users': [],
        'username': user.username,
        'profile': {'first_name': user.first_name, 'last_name': user.last_name}
    }


def to_foreign_resource_response(resource: Resource) -> Dict[str, Any]:
    return {
        'id': resource.id,
        'name': resource.name,
        'username': resource.username,
        'uri': resource.uri,
        'description': resource.description,
        'secrets': [{'data': resource.encrypted_secret}],
        'tags': [{'slug': tag for tag in resource.tags}] if resource.tags else [],
    }


def to_foreign_group_response(group: Group) -> Dict[str, Any]:
    return to_foreign_group(group)
