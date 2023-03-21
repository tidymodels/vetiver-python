from .vetiver_model import VetiverModel
from .meta import VetiverMeta
from .utils import inform
import warnings
import logging
from typing import List

_log = logging.getLogger(__name__)


class ModelCard(UserWarning):
    def __init__(
        self,
        message="""
        Model Cards provide a framework for transparent, responsible reporting.
        Use the vetiver `.qmd` Quarto template as a place to start,
        with vetiver.model_card()""",
    ):
        self.message = message
        super().__init__(self.message)


def vetiver_pin_write(board, model: VetiverModel, versioned: bool = True):
    """
    Pin a trained VetiverModel along with other model metadata.

    Parameters
    ----------
    board:
        A pin board, created by `pins.board_folder()` or another `board_` function.
    model: vetiver.VetiverModel
        VetiverModel to be written to board
    versioned: bool
        Whether or not the pin should be versioned

    Examples
    -------
    >>> import vetiver
    >>> from pins import board_temp
    >>> model_board = board_temp(versioned = True, allow_pickle_read = True)
    >>> X, y = vetiver.get_mock_data()
    >>> model = vetiver.get_mock_model().fit(X, y)
    >>> v = vetiver.VetiverModel(model, "my_model", prototype_data = X)
    >>> vetiver.vetiver_pin_write(model_board, v)
    """
    if not board.allow_pickle_read:
        raise NotImplementedError  # must be pickle-able

    inform(
        _log,
        "Model Cards provide a framework for transparent, responsible "
        "reporting. \n Use the vetiver `.qmd` Quarto template as a place to start, \n "
        "with vetiver.model_card()",
    )

    # convert older model's ptype to prototype
    if hasattr(model, "ptype"):
        model.prototype = model.ptype
        delattr(model, "ptype")
    # metadata is dict
    if isinstance(model.metadata, dict):
        model.metadata = VetiverMeta.from_dict(model.metadata)

    required_pkgs = get_board_pkgs(board) + model.metadata.required_pkgs

    board.pin_write(
        model.model,
        name=model.model_name,
        type="joblib",
        description=model.description,
        metadata={
            "user": model.metadata.user,
            "vetiver_meta": {
                "required_pkgs": required_pkgs,
                "prototype": None if not model.prototype else model.prototype().json(),
                "python_version": None
                if not model.metadata.python_version
                else list(model.metadata.python_version),
            },
        },
        versioned=versioned,
    )


def vetiver_pin_read(board, name: str, version: str = None) -> VetiverModel:
    """
    Read pin and populate VetiverModel

    Parameters
    ----------
    board:
        A pin board, created by `pins.board_folder()` or another `board_` function.
    name: string
        Pin name
    version: str
        Retrieve a specific version of a pin.

    Returns
    --------
    vetiver.VetiverModel

    Notes
    -----
    If reading a board from RSConnect, the `board` argument must be in
    "username/modelname" format.

    """

    warnings.warn(
        "vetiver_pin_read will be removed in v1.0.0. Use classmethod "
        "VetiverModel.from_pin() instead",
        DeprecationWarning,
    )

    v = VetiverModel.from_pin(board=board, name=name, version=version)

    return v


def get_board_pkgs(board) -> List[str]:
    """
    Extract packages required for pin board authorization

    Parameters
    ----------
    board:
        A pin board, created by `pins.board_folder()` or another `board_` function.

    Returns
    --------
    list[str]
    """
    prot = board.fs.protocol

    if prot == "rsc":
        return ["rsconnect-python"]
    elif prot == "file":
        return []
    elif prot == ["s3", "s3a"]:
        return ["s3fs"]
    elif prot == "abfs":
        return ["adlfs"]
    elif prot == ("gcs", "gs"):
        return ["gcsfs"]
    else:
        warnings.warn(
            f"required packages unknown for protocol: {prot}, "
            "add to model's metadata to ensure they are exported"
        )
        return []
