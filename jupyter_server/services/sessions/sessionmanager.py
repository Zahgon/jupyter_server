"""A base class session manager."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os
import pathlib
import uuid
from typing import Any, NewType, Optional, Union, cast

KernelName = NewType("KernelName", str)
ModelName = NewType("ModelName", str)

try:
    import sqlite3
except ImportError:
    # fallback on pysqlite2 if Python was build without sqlite
    from pysqlite2 import dbapi2 as sqlite3  # type:ignore[no-redef]

from dataclasses import dataclass, fields

from jupyter_core.utils import ensure_async
from tornado import web
from traitlets import Instance, TraitError, Unicode, validate
from traitlets.config.configurable import LoggingConfigurable

from jupyter_server.traittypes import InstanceFromClasses


class KernelSessionRecordConflict(Exception):
    """Exception class to use when two KernelSessionRecords cannot
    merge because of conflicting data.
    """


@dataclass
class KernelSessionRecord:  # noqa: PLW1641 - TODO: implement __hash__
    """A record object for tracking a Jupyter Server Kernel Session.

    Two records that share a session_id must also share a kernel_id, while
    kernels can have multiple session (and thereby) session_ids
    associated with them.
    """

    session_id: Optional[str] = None
    kernel_id: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        """Whether a record equals another."""
        if isinstance(other, KernelSessionRecord):
            condition1 = self.kernel_id and self.kernel_id == other.kernel_id
            condition2 = all(
                [
                    self.session_id == other.session_id,
                    self.kernel_id is None or other.kernel_id is None,
                ]
            )
            if any([condition1, condition2]):
                return True
            # If two records share session_id but have different kernels, this is
            # and ill-posed expression. This should never be true. Raise an exception
            # to inform the user.
            if all(
                [
                    self.session_id,
                    self.session_id == other.session_id,
                    self.kernel_id != other.kernel_id,
                ]
            ):
                msg = (
                    "A single session_id can only have one kernel_id "
                    "associated with. These two KernelSessionRecords share the same "
                    "session_id but have different kernel_ids. This should "
                    "not be possible and is likely an issue with the session "
                    "records."
                )
                raise KernelSessionRecordConflict(msg)
        return False

    def update(self, other: "KernelSessionRecord") -> None:
        """Updates in-place a kernel from other (only accepts positive updates"""
        pass


class KernelSessionRecordList:
    """An object for storing and managing a list of KernelSessionRecords.

    When adding a record to the list, the KernelSessionRecordList
    first checks if the record already exists in the list. If it does,
    the record will be updated with the new information; otherwise,
    it will be appended.
    """

    _records: list[KernelSessionRecord]

    def __init__(self, *records: KernelSessionRecord):
        """Initialize a record list."""
        self._records = []
        for record in records:
            self.update(record)

    def __str__(self):
        """The string representation of a record list."""
        return str(self._records)

    def __contains__(self, record: Union[KernelSessionRecord, str]) -> bool:
        """Search for records by kernel_id and session_id"""
        if isinstance(record, KernelSessionRecord) and record in self._records:
            return True

        if isinstance(record, str):
            for r in self._records:
                if record in [r.session_id, r.kernel_id]:
                    return True
        return False

    def __len__(self):
        """The length of the record list."""
        return len(self._records)

    def get(self, record: Union[KernelSessionRecord, str]) -> KernelSessionRecord:
        """Return a full KernelSessionRecord from a session_id, kernel_id, or
        incomplete KernelSessionRecord.
        """
        pass

    def update(self, record: KernelSessionRecord) -> None:
        """Update a record in-place or append it if not in the list."""
        pass

    def remove(self, record: KernelSessionRecord) -> None:
        """Remove a record if its found in the list. If it's not found,
        do nothing.
        """
        pass


class SessionManager(LoggingConfigurable):
    """A session manager."""

    database_filepath = Unicode(
        default_value=":memory:",
        help=(
            "The filesystem path to SQLite Database file "
            "(e.g. /path/to/session_database.db). By default, the session "
            "database is stored in-memory (i.e. `:memory:` setting from sqlite3) "
            "and does not persist when the current Jupyter Server shuts down."
        ),
    ).tag(config=True)

    @validate("database_filepath")
    def _validate_database_filepath(self, proposal):
        """Validate a database file path."""
        pass

    kernel_manager = Instance("jupyter_server.services.kernels.kernelmanager.MappingKernelManager")
    contents_manager = InstanceFromClasses(
        [
            "jupyter_server.services.contents.manager.ContentsManager",
            "notebook.services.contents.manager.ContentsManager",
        ]
    )

    def __init__(self, *args, **kwargs):
        """Initialize a record list."""
        super().__init__(*args, **kwargs)
        self._pending_sessions = KernelSessionRecordList()

    # Session database initialized below
    _cursor = None
    _connection = None
    _columns = {"session_id", "path", "name", "type", "kernel_id"}

    @property
    def cursor(self):
        """Start a cursor and create a database called 'session'"""
        pass

    @property
    def connection(self):
        """Start a database connection"""
        pass

    def close(self):
        """Close the sqlite connection"""
        pass

    def __del__(self):
        """Close connection once SessionManager closes"""
        self.close()

    async def session_exists(self, path):
        """Check to see if the session of a given name exists"""
        pass

    def new_session_id(self) -> str:
        """Create a uuid for a new session"""
        pass

    async def create_session(
        self,
        path: Optional[str] = None,
        name: Optional[ModelName] = None,
        type: Optional[str] = None,
        kernel_name: Optional[KernelName] = None,
        kernel_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Creates a session and returns its model

        Parameters
        ----------
        name: ModelName(str)
            Usually the model name, like the filename associated with current
            kernel.
        """
        pass

    def get_kernel_env(
        self, path: Optional[str], name: Optional[ModelName] = None
    ) -> dict[str, str]:
        """Return the environment variables that need to be set in the kernel

        Parameters
        ----------
        path : str
            the url path for the given session.
        name: ModelName(str), optional
            Here the name is likely to be the name of the associated file
            with the current kernel at startup time.
        """
        pass

    async def start_kernel_for_session(
        self,
        session_id: str,
        path: Optional[str],
        name: Optional[ModelName],
        type: Optional[str],
        kernel_name: Optional[KernelName],
    ) -> str:
        """Start a new kernel for a given session.

        Parameters
        ----------
        session_id : str
            uuid for the session; this method must be given a session_id
        path : str
            the path for the given session - seem to be a session id sometime.
        name : str
            Usually the model name, like the filename associated with current
            kernel.
        type : str
            the type of the session
        kernel_name : str
            the name of the kernel specification to use.  The default kernel name will be used if not provided.
        """
        pass

    async def save_session(self, session_id, path=None, name=None, type=None, kernel_id=None):
        """Saves the items for the session with the given session_id

        Given a session_id (and any other of the arguments), this method
        creates a row in the sqlite session database that holds the information
        for a session.

        Parameters
        ----------
        session_id : str
            uuid for the session; this method must be given a session_id
        path : str
            the path for the given session
        name : str
            the name of the session
        type : str
            the type of the session
        kernel_id : str
            a uuid for the kernel associated with this session

        Returns
        -------
        model : dict
            a dictionary of the session model
        """
        pass

    async def get_session(self, **kwargs):
        """Returns the model for a particular session.

        Takes a keyword argument and searches for the value in the session
        database, then returns the rest of the session's info.

        Parameters
        ----------
        **kwargs : dict
            must be given one of the keywords and values from the session database
            (i.e. session_id, path, name, type, kernel_id)

        Returns
        -------
        model : dict
            returns a dictionary that includes all the information from the
            session described by the kwarg.
        """
        pass

    async def update_session(self, session_id, **kwargs):
        """Updates the values in the session database.

        Changes the values of the session with the given session_id
        with the values from the keyword arguments.

        Parameters
        ----------
        session_id : str
            a uuid that identifies a session in the sqlite3 database
        **kwargs : str
            the key must correspond to a column title in session database,
            and the value replaces the current value in the session
            with session_id.
        """
        pass

    async def kernel_culled(self, kernel_id: str) -> bool:
        """Checks if the kernel is still considered alive and returns true if its not found."""
        pass

    async def row_to_model(self, row, tolerate_culled=False):
        """Takes sqlite database session row and turns it into a dictionary"""
        pass

    async def list_sessions(self):
        """Returns a list of dictionaries containing all the information from
        the session database"""
        pass

    async def delete_session(self, session_id):
        """Deletes the row in the session database with given session_id"""
        pass
