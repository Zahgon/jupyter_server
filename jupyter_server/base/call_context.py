"""Provides access to variables pertaining to specific call contexts."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from contextvars import Context, ContextVar, copy_context
from typing import Any


class CallContext:
    """CallContext essentially acts as a namespace for managing context variables.

    Although not required, it is recommended that any "file-spanning" context variable
    names (i.e., variables that will be set or retrieved from multiple files or services) be
    added as constants to this class definition.
    """

    # Add well-known (file-spanning) names here.
    #: Provides access to the current request handler once set.
    JUPYTER_HANDLER: str = "JUPYTER_HANDLER"

    # A map of variable name to value is maintained as the single ContextVar.  This also enables
    # easier management over maintaining a set of ContextVar instances, since the Context is a
    # map of ContextVar instances to their values, and the "name" is no longer a lookup key.
    _NAME_VALUE_MAP = "_name_value_map"
    _name_value_map: ContextVar[dict[str, Any]] = ContextVar(_NAME_VALUE_MAP)

    @classmethod
    def get(cls, name: str) -> Any:
        """Returns the value corresponding the named variable relative to this context.

        If the named variable doesn't exist, None will be returned.

        Parameters
        ----------
        name : str
            The name of the variable to get from the call context

        Returns
        -------
        value: Any
            The value associated with the named variable for this call context
        """
        pass

    @classmethod
    def set(cls, name: str, value: Any) -> None:
        """Sets the named variable to the specified value in the current call context.

        Parameters
        ----------
        name : str
            The name of the variable to store into the call context
        value : Any
            The value of the variable to store into the call context

        Returns
        -------
        None
        """
        pass

    @classmethod
    def context_variable_names(cls) -> list[str]:
        """Returns a list of variable names set for this call context.

        Returns
        -------
        names: List[str]
            A list of variable names set for this call context.
        """
        pass

    @classmethod
    def _get_map(cls) -> dict[str, Any]:
        """Get the map of names to their values from the _NAME_VALUE_MAP context var.

        If the map does not exist in the current context, an empty map is created and returned.
        """
        pass
