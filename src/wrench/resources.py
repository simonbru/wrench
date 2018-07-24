# wrench -- A CLI for Passbolt
# Copyright (C) 2018 Liip SA <wrench@liip.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

from typing import Callable, Iterable, Sequence, Union

from gnupg import GPG

from . import utils
from .context import Context
from .models import Group, Permission, PermissionType, Resource, Secret, User
from .services import add_resource as add_resource_service
from .services import get_permissions
from .services import share_resource as share_resource_service
from .users import unfold_groups


def resource_matches(resource: Resource, terms: str) -> bool:
    """
    Return `True` if terms are found in the given resource. Search is case insensitive, and terms are split at the
    space character. The resource matches only if all given terms are found in the combination of all the resource
    fields.
    """
    if not terms:
        return True

    terms_list = terms.casefold().split(' ')
    resource_str = ' '.join(
        value.casefold() for value in (
            getattr(resource, attr) for attr in ('name', 'username', 'uri', 'description')
        )
        if value
    )

    return all(term in resource_str for term in terms_list)


def search_resources(resources: Iterable[Resource], terms: str) -> Sequence[Resource]:
    """
    Return a sequence of resources matching the given `terms`.
    """
    return [resource for resource in resources if resource_matches(resource, terms)]


def decrypt_resource(resource: Resource, gpg: GPG) -> Resource:
    """
    Return a new `Resource` object with its field `secret` decrypted.
    """
    return resource._replace(secret=utils.decrypt(resource.encrypted_secret, gpg))


def share_resource(resource: Resource, recipients: Iterable[Union[User, Group]],
                   encrypt_func: Callable[[str, User], str], context: Context) -> Sequence[Union[Group, User]]:
    """
    Share the given resource with the given recipients.
    """
    if not recipients:
        return []

    # Sending an existing Secret or Permission to the Passbolt API returns an error so we need to make sure to strip
    # any recipients that already have the resource shared with them
    existing_permissions = get_permissions(session=context.session, resource_id=resource.id,
                                           users_cache=context.users_by_id, groups_cache=context.groups_by_id)
    existing_recipients = [permission.recipient for permission in existing_permissions]
    existing_user_recipients = unfold_groups(existing_recipients, context.users_by_id)

    new_recipients = set(recipients) - set(existing_recipients)
    unfolded_recipients = unfold_groups(new_recipients, context.users_by_id)
    new_user_recipients = set(unfolded_recipients) - set(existing_user_recipients)

    secrets = [
        Secret(resource=resource, recipient=recipient, secret=encrypt_func(resource.secret, recipient))
        for recipient in new_user_recipients
    ]
    permissions = [
        Permission(resource=resource, recipient=recipient, permission_type=PermissionType.READ.value)
        for recipient in new_recipients
    ]

    share_resource_service(context.session, resource.id, secrets, permissions)

    return list(new_recipients)


def add_resource(resource: Resource, encrypt_func: Callable[[str], str], context: Context) -> Resource:
    resource = resource._replace(encrypted_secret=encrypt_func(resource.secret))
    return add_resource_service(context.session, resource)
