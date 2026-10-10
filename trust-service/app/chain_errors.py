"""Error types for chain access and decoding of Solidity custom-error reverts."""
from __future__ import annotations

from typing import Any

from eth_abi import decode
from eth_utils.abi import function_abi_to_4byte_selector


class ChainError(Exception):
    """Base error for chain problems. `code` is a stable machine-readable string."""

    code = "CHAIN_ERROR"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class ChainUnavailable(ChainError):
    """Node unreachable, contract not deployed, or configuration missing."""

    code = "CHAIN_UNAVAILABLE"


class ContractRejected(ChainError):
    """The contract reverted with a custom error (e.g. ReportExists, AlreadySuperseded)."""

    def __init__(self, message: str, error_name: str, args: tuple[Any, ...] = ()) -> None:
        super().__init__(message, code=to_error_code(error_name))
        self.error_name = error_name
        self.error_args = args


def to_error_code(error_name: str) -> str:
    """ReportExists -> REPORT_EXISTS."""
    out = "".join(f"_{c}" if c.isupper() and i else c for i, c in enumerate(error_name))
    return out.upper() or "CONTRACT_REVERTED"


def error_selectors(abi: list[dict[str, Any]]) -> dict[bytes, dict[str, Any]]:
    """Map 4-byte selector -> ABI entry for every custom error in the ABI."""
    return {function_abi_to_4byte_selector(item): item for item in abi if item.get("type") == "error"}


def decode_revert(data: object, selectors: dict[bytes, dict[str, Any]], fallback: str) -> ContractRejected:
    """Decode revert data ("0x" + selector + args) into ContractRejected."""
    if isinstance(data, str) and data.startswith("0x") and len(data) >= 10:
        abi_item = selectors.get(bytes.fromhex(data[2:10]))
        if abi_item:
            types = [i["type"] for i in abi_item.get("inputs", [])]
            args = tuple(decode(types, bytes.fromhex(data[10:]))) if types else ()
            name = str(abi_item["name"])
            detail = f" ({', '.join(map(str, args))})" if args else ""
            return ContractRejected(f"Contract rejected the call: {name}{detail}", name, args)
    return ContractRejected(f"Contract rejected the call: {fallback}", "ContractReverted")
