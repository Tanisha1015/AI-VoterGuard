"""ReportRegistry client (CONTRACT.md 6.6) built on web3.py.

Address and ABI come from chain/deployments/. Transactions are signed locally with
SUBMITTER_PRIVATE_KEY (Hardhat account #1 on the local node, supplied via env).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception

from .chain_errors import ChainError, ChainUnavailable, ContractRejected, decode_revert, error_selectors
from .config import Settings
from .hashing import from_bytes32, to_bytes32

__all__ = ["ChainClient", "ChainError", "ChainUnavailable", "ContractRejected", "RecordResult", "iso_utc"]

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecordResult:
    tx_hash: str
    block_number: int
    recorded_at: str


def iso_utc(timestamp: int) -> str:
    """Unix seconds -> ISO-8601 UTC with Z suffix."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path, what: str) -> Any:
    if not path.is_file():
        raise ChainUnavailable(f"{what} not found at {path}. Start the node and run `npm run deploy:local` in chain/.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ChainUnavailable(f"{what} at {path} is not valid JSON: {exc}") from exc


class ChainClient:
    """Connects lazily so the service can start (and report status) while the node is down."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._w3 = Web3(Web3.HTTPProvider(settings.chain_rpc_url, request_kwargs={"timeout": 10}))
        self._contract: Any = None
        self._selectors: dict[bytes, dict[str, Any]] = {}

    def _connect(self) -> Any:
        """Return the contract, loading it on first use. Raises ChainUnavailable."""
        try:
            connected = self._w3.is_connected()
        except Exception:  # noqa: BLE001 - any transport failure means "unavailable"
            connected = False
        if not connected:
            raise ChainUnavailable(f"Chain node is not reachable at {self.settings.chain_rpc_url}.")
        if self._contract is None:
            deployment = _read_json(self.settings.deployment_file, "Deployment file")
            abi = _read_json(self.settings.abi_file, "Contract ABI")
            address = Web3.to_checksum_address(deployment["address"])
            if not self._w3.eth.get_code(address):
                raise ChainUnavailable(
                    f"No contract code at {address}. The node may have restarted; run `npm run deploy:local` in chain/."
                )
            self._contract = self._w3.eth.contract(address=address, abi=abi)
            self._selectors = error_selectors(abi)
        return self._contract

    def _rejected(self, exc: ContractLogicError) -> ContractRejected:
        return decode_revert(exc.data, self._selectors, str(exc))

    def record_report(
        self, report_id: str, report_hash: str, draft_hash: str, final_hash: str, asdd_hash: str, supersedes: str | None
    ) -> RecordResult:
        """Simulate, sign and send recordReport, then wait for the receipt."""
        key = self.settings.submitter_private_key
        if not key:
            raise ChainUnavailable("SUBMITTER_PRIVATE_KEY is not set; cannot sign the transaction.")
        contract = self._connect()
        w3 = self._w3
        try:
            account = w3.eth.account.from_key(key)
        except Exception as exc:  # noqa: BLE001
            raise ChainUnavailable("SUBMITTER_PRIVATE_KEY is not a valid private key.") from exc

        call = contract.functions.recordReport(
            report_id, to_bytes32(report_hash), to_bytes32(draft_hash), to_bytes32(final_hash),
            to_bytes32(asdd_hash), supersedes or "",
        )
        try:
            call.call({"from": account.address})  # surfaces reverts with a decoded reason, spends nothing
            tx = call.build_transaction({
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address, "pending"),
                "chainId": w3.eth.chain_id,
            })
            tx_hash = w3.eth.send_raw_transaction(account.sign_transaction(tx).raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        except ContractLogicError as exc:
            raise self._rejected(exc) from exc
        except Web3Exception as exc:
            raise ChainError(f"Chain transaction failed: {exc}") from exc
        except (OSError, TimeoutError) as exc:
            raise ChainUnavailable(f"Lost connection to the chain node: {exc}") from exc

        if receipt["status"] != 1:
            raise ChainError(f"Transaction {tx_hash.to_0x_hex()} reverted.")
        block = w3.eth.get_block(receipt["blockNumber"])
        return RecordResult(
            tx_hash=receipt["transactionHash"].to_0x_hex(),
            block_number=int(receipt["blockNumber"]),
            recorded_at=iso_utc(int(block["timestamp"])),
        )

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        """Recorded report as a dict, or None if the id is unknown on chain."""
        contract = self._connect()
        try:
            values = contract.functions.getReport(report_id).call()
        except ContractLogicError as exc:
            rejected = self._rejected(exc)
            if rejected.error_name == "UnknownReport":
                return None
            raise rejected from exc
        except (OSError, Web3Exception) as exc:
            raise ChainUnavailable(f"Could not read from the chain node: {exc}") from exc
        report_hash, draft_hash, final_hash, asdd_hash, timestamp, submitter, supersedes_id = values
        return {
            "report_hash": from_bytes32(report_hash),
            "draft_hash": from_bytes32(draft_hash),
            "final_hash": from_bytes32(final_hash),
            "asdd_hash": from_bytes32(asdd_hash),
            "recorded_at": iso_utc(int(timestamp)),
            "submitter": str(submitter).lower(),
            "supersedes": supersedes_id or None,
        }

    def superseded_by(self, report_id: str) -> str | None:
        """Id of the report that superseded `report_id`, or None."""
        contract = self._connect()
        try:
            value = contract.functions.supersededBy(report_id).call()
        except (OSError, Web3Exception) as exc:
            raise ChainUnavailable(f"Could not read from the chain node: {exc}") from exc
        return value or None

    def status(self) -> dict[str, Any]:
        """Chain info for GET /api/chain/status. Never raises; reports connected=false instead."""
        try:
            contract = self._connect()
            return {
                "connected": True,
                "chain_id": int(self._w3.eth.chain_id),
                "contract_address": str(contract.address).lower(),
                "latest_block": int(self._w3.eth.block_number),
            }
        except (ChainError, OSError, Web3Exception) as exc:
            log.warning("Chain status: %s", exc)
            address = None
            try:
                address = str(_read_json(self.settings.deployment_file, "Deployment file")["address"]).lower()
            except (ChainUnavailable, KeyError):
                pass
            return {"connected": False, "chain_id": None, "contract_address": address, "latest_block": None}

