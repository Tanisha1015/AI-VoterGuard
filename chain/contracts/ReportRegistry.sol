// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ReportRegistry
/// @notice Records SHA-256 hashes of VoterGuard audit reports so anyone can later check
///         that a report file is unchanged. Reports are immutable; a corrected report
///         is recorded under a new id that supersedes the old one.
/// @dev Stores hashes only. It makes no judgement about any voter or roll; it only
///      proves which report bytes were published, when, and by whom.
contract ReportRegistry {
    /// @notice A recorded audit report (see contracts/CONTRACT.md section 6.6).
    struct Report {
        bytes32 reportHash; // SHA-256 of the canonical report JSON bytes
        bytes32 draftHash; // SHA-256 of the draft roll CSV
        bytes32 finalHash; // SHA-256 of the final roll CSV
        bytes32 asddHash; // SHA-256 of the ASDD list CSV
        uint64 timestamp; // block timestamp when recorded
        address submitter; // account that recorded the report
        string supersedesId; // id of the report this one replaces, or ""
    }

    /// @notice Account that manages the submitter allow-list.
    address public immutable owner;

    /// @notice Accounts allowed to record reports.
    mapping(address => bool) public submitters;

    mapping(string => Report) private reports;
    mapping(string => bool) private exists;
    mapping(string => string) private _supersededBy;

    /// @notice Emitted when a report is recorded.
    /// @param reportId Indexed (appears as keccak256 hash in the log topic).
    /// @param reportIdPlain The same id, unindexed, so it is readable from the log data.
    event ReportRecorded(
        string indexed reportId,
        string reportIdPlain,
        bytes32 reportHash,
        address submitter,
        uint64 timestamp
    );
    /// @notice Emitted when an account is added to the allow-list.
    event SubmitterAdded(address indexed account);
    /// @notice Emitted when an account is removed from the allow-list.
    event SubmitterRemoved(address indexed account);

    error NotOwner();
    error NotSubmitter();
    error ZeroAddress();
    error EmptyReportId();
    error ReportExists(string reportId);
    error UnknownReport(string reportId);
    error UnknownSupersededReport(string supersedesId);
    error AlreadySuperseded(string supersedesId, string supersededBy);

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlySubmitter() {
        if (!submitters[msg.sender]) revert NotSubmitter();
        _;
    }

    /// @notice Sets the deployer as owner and as the first submitter.
    constructor() {
        owner = msg.sender;
        submitters[msg.sender] = true;
        emit SubmitterAdded(msg.sender);
    }

    /// @notice Allows `account` to record reports. Owner only.
    function addSubmitter(address account) external onlyOwner {
        if (account == address(0)) revert ZeroAddress();
        submitters[account] = true;
        emit SubmitterAdded(account);
    }

    /// @notice Revokes `account`'s permission to record reports. Owner only.
    function removeSubmitter(address account) external onlyOwner {
        submitters[account] = false;
        emit SubmitterRemoved(account);
    }

    /// @notice Records a new, immutable report.
    /// @param reportId Unique report id, e.g. "VG-2026-0001". Must be non-empty and unused.
    /// @param reportHash SHA-256 of the canonical report JSON bytes.
    /// @param draftHash SHA-256 of the draft roll CSV.
    /// @param finalHash SHA-256 of the final roll CSV.
    /// @param asddHash SHA-256 of the ASDD list CSV.
    /// @param supersedesId Id of an existing, not yet superseded report this replaces, or "".
    function recordReport(
        string calldata reportId,
        bytes32 reportHash,
        bytes32 draftHash,
        bytes32 finalHash,
        bytes32 asddHash,
        string calldata supersedesId
    ) external onlySubmitter {
        if (bytes(reportId).length == 0) revert EmptyReportId();
        if (exists[reportId]) revert ReportExists(reportId);

        if (bytes(supersedesId).length != 0) {
            if (!exists[supersedesId]) revert UnknownSupersededReport(supersedesId);
            if (bytes(_supersededBy[supersedesId]).length != 0) {
                revert AlreadySuperseded(supersedesId, _supersededBy[supersedesId]);
            }
            _supersededBy[supersedesId] = reportId;
        }

        uint64 timestamp = uint64(block.timestamp);
        reports[reportId] = Report({
            reportHash: reportHash,
            draftHash: draftHash,
            finalHash: finalHash,
            asddHash: asddHash,
            timestamp: timestamp,
            submitter: msg.sender,
            supersedesId: supersedesId
        });
        exists[reportId] = true;

        emit ReportRecorded(reportId, reportId, reportHash, msg.sender, timestamp);
    }

    /// @notice Returns a recorded report. Reverts with UnknownReport if absent.
    function getReport(string calldata reportId) external view returns (Report memory) {
        if (!exists[reportId]) revert UnknownReport(reportId);
        return reports[reportId];
    }

    /// @notice Checks a candidate hash against the recorded report hash.
    /// @return True only if the report exists and its hash equals `candidateHash`.
    function verifyReport(string calldata reportId, bytes32 candidateHash) external view returns (bool) {
        return exists[reportId] && reports[reportId].reportHash == candidateHash;
    }

    /// @notice Returns the id of the report that superseded `reportId`, or "" if none.
    function supersededBy(string calldata reportId) external view returns (string memory) {
        return _supersededBy[reportId];
    }
}
