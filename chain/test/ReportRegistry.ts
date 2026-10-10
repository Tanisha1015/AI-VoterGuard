import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { network } from "hardhat";
import { getAddress, keccak256, toHex, zeroAddress, type Hex } from "viem";

/** Deterministic synthetic 32-byte hash for test data (stands in for a SHA-256). */
function fakeHash(label: string): Hex {
  return keccak256(toHex(label));
}

const REPORT_1 = "VG-2026-0001";
const REPORT_2 = "VG-2026-0002";
const REPORT_3 = "VG-2026-0003";
const UNKNOWN = "VG-2026-9999";
const H = {
  report: fakeHash("report-1"),
  draft: fakeHash("draft_roll.csv"),
  final: fakeHash("final_roll.csv"),
  asdd: fakeHash("asdd.csv"),
};

describe("ReportRegistry", async function () {
  const { viem, networkHelpers } = await network.create();
  const publicClient = await viem.getPublicClient();

  /** Fresh registry: wallet 0 is owner, wallet 1 an approved submitter, wallet 2 an outsider. */
  async function deployFixture() {
    const [owner, submitter, outsider] = await viem.getWalletClients();
    const registry = await viem.deployContract("ReportRegistry");
    await registry.write.addSubmitter([submitter.account.address]);
    return { registry, owner, submitter, outsider };
  }

  type Registry = Awaited<ReturnType<typeof deployFixture>>["registry"];

  /** Records REPORT_1 from the owner with the shared synthetic hashes. */
  function recordFirst(registry: Registry) {
    return registry.write.recordReport([REPORT_1, H.report, H.draft, H.final, H.asdd, ""]);
  }

  it("records a report and returns it from getReport", async function () {
    const { registry, owner } = await networkHelpers.loadFixture(deployFixture);
    await recordFirst(registry);

    const report = await registry.read.getReport([REPORT_1]);
    assert.equal(report.reportHash, H.report);
    assert.equal(report.draftHash, H.draft);
    assert.equal(report.finalHash, H.final);
    assert.equal(report.asddHash, H.asdd);
    assert.equal(getAddress(report.submitter), getAddress(owner.account.address));
    assert.equal(report.supersedesId, "");
  });

  it("getReport reverts with UnknownReport for an unknown id", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await viem.assertions.revertWithCustomErrorWithArgs(
      registry.read.getReport([UNKNOWN]),
      registry,
      "UnknownReport",
      [UNKNOWN],
    );
  });

  it("verifyReport returns true on match, false on different hash or unknown id", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await recordFirst(registry);

    assert.equal(await registry.read.verifyReport([REPORT_1, H.report]), true);
    assert.equal(await registry.read.verifyReport([REPORT_1, fakeHash("edited report")]), false);
    assert.equal(await registry.read.verifyReport([UNKNOWN, H.report]), false);
  });

  it("reverts with ReportExists when the same id is recorded twice", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await recordFirst(registry);
    await viem.assertions.revertWithCustomErrorWithArgs(recordFirst(registry), registry, "ReportExists", [
      REPORT_1,
    ]);
  });

  it("reverts with EmptyReportId when the id is empty", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await viem.assertions.revertWithCustomError(
      registry.write.recordReport(["", H.report, H.draft, H.final, H.asdd, ""]),
      registry,
      "EmptyReportId",
    );
  });

  it("reverts with NotSubmitter when a non-submitter records", async function () {
    const { registry, outsider } = await networkHelpers.loadFixture(deployFixture);
    await viem.assertions.revertWithCustomError(
      registry.write.recordReport([REPORT_1, H.report, H.draft, H.final, H.asdd, ""], {
        account: outsider.account,
      }),
      registry,
      "NotSubmitter",
    );
  });

  it("lets the owner add and remove submitters, and blocks non-owners", async function () {
    const { registry, owner, submitter, outsider } = await networkHelpers.loadFixture(deployFixture);
    const asSubmitter = { account: submitter.account };
    const asOutsider = { account: outsider.account };

    assert.equal(await registry.read.submitters([owner.account.address]), true);
    assert.equal(await registry.read.submitters([submitter.account.address]), true);
    await registry.write.recordReport([REPORT_1, H.report, H.draft, H.final, H.asdd, ""], asSubmitter);

    await registry.write.removeSubmitter([submitter.account.address]);
    assert.equal(await registry.read.submitters([submitter.account.address]), false);
    await viem.assertions.revertWithCustomError(
      registry.write.recordReport([REPORT_2, H.report, H.draft, H.final, H.asdd, ""], asSubmitter),
      registry,
      "NotSubmitter",
    );

    await viem.assertions.revertWithCustomError(
      registry.write.addSubmitter([outsider.account.address], asOutsider),
      registry,
      "NotOwner",
    );
    await viem.assertions.revertWithCustomError(
      registry.write.removeSubmitter([owner.account.address], asOutsider),
      registry,
      "NotOwner",
    );
    await viem.assertions.revertWithCustomError(registry.write.addSubmitter([zeroAddress]), registry, "ZeroAddress");
  });

  it("records a superseding report and links old to new", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await recordFirst(registry);
    assert.equal(await registry.read.supersededBy([REPORT_1]), "");

    await registry.write.recordReport([REPORT_2, fakeHash("report-2"), H.draft, H.final, H.asdd, REPORT_1]);

    assert.equal(await registry.read.supersededBy([REPORT_1]), REPORT_2);
    assert.equal(await registry.read.supersededBy([REPORT_2]), "");
    assert.equal((await registry.read.getReport([REPORT_2])).supersedesId, REPORT_1);
    // The original report stays readable and verifiable.
    assert.equal(await registry.read.verifyReport([REPORT_1, H.report]), true);
  });

  it("reverts with UnknownSupersededReport when superseding an unknown id", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await viem.assertions.revertWithCustomErrorWithArgs(
      registry.write.recordReport([REPORT_2, H.report, H.draft, H.final, H.asdd, UNKNOWN]),
      registry,
      "UnknownSupersededReport",
      [UNKNOWN],
    );
  });

  it("reverts with AlreadySuperseded when a report is superseded twice", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    await recordFirst(registry);
    await registry.write.recordReport([REPORT_2, fakeHash("report-2"), H.draft, H.final, H.asdd, REPORT_1]);

    await viem.assertions.revertWithCustomErrorWithArgs(
      registry.write.recordReport([REPORT_3, fakeHash("report-3"), H.draft, H.final, H.asdd, REPORT_1]),
      registry,
      "AlreadySuperseded",
      [REPORT_1, REPORT_2],
    );
    assert.equal(await registry.read.verifyReport([REPORT_3, fakeHash("report-3")]), false);
  });

  it("emits ReportRecorded with the correct arguments", async function () {
    const { registry, submitter } = await networkHelpers.loadFixture(deployFixture);
    const txHash = await registry.write.recordReport([REPORT_1, H.report, H.draft, H.final, H.asdd, ""], {
      account: submitter.account,
    });
    const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
    const block = await publicClient.getBlock({ blockNumber: receipt.blockNumber });

    const events = await registry.getEvents.ReportRecorded({}, { blockHash: receipt.blockHash });
    assert.equal(events.length, 1);
    const { args } = events[0];
    // The indexed string topic holds keccak256(id); the unindexed copy is readable.
    assert.equal(args.reportId, keccak256(toHex(REPORT_1)));
    assert.equal(args.reportIdPlain, REPORT_1);
    assert.equal(args.reportHash, H.report);
    assert.ok(args.submitter !== undefined);
    assert.equal(getAddress(args.submitter), getAddress(submitter.account.address));
    assert.equal(args.timestamp, block.timestamp);
  });

  it("emits ReportRecorded (viem assertion helper)", async function () {
    const { registry, owner } = await networkHelpers.loadFixture(deployFixture);
    const next = BigInt(await networkHelpers.time.latest()) + 100n;
    await networkHelpers.time.setNextBlockTimestamp(next);
    await viem.assertions.emitWithArgs(recordFirst(registry), registry, "ReportRecorded", [
      keccak256(toHex(REPORT_1)),
      REPORT_1,
      H.report,
      getAddress(owner.account.address),
      next,
    ]);
  });

  it("stores the block timestamp on the report", async function () {
    const { registry } = await networkHelpers.loadFixture(deployFixture);
    const target = BigInt(await networkHelpers.time.latest()) + 3600n;
    await networkHelpers.time.setNextBlockTimestamp(target);

    await recordFirst(registry);

    const report = await registry.read.getReport([REPORT_1]);
    assert.equal(report.timestamp, target);
  });
});
