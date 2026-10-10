import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import hre, { network } from "hardhat";
import { getAddress } from "viem";

/** Chain id of the local Hardhat node started by `npm run node`. */
const EXPECTED_CHAIN_ID = 31337;
const DEPLOYMENTS_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "deployments");

/** Writes `data` as pretty JSON to deployments/<fileName>. */
async function writeJson(fileName: string, data: unknown): Promise<string> {
  await mkdir(DEPLOYMENTS_DIR, { recursive: true });
  const filePath = path.join(DEPLOYMENTS_DIR, fileName);
  await writeFile(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
  return filePath;
}

/**
 * Deploys ReportRegistry from account 0, allow-lists account 1 as a submitter,
 * then writes deployments/local.json and deployments/ReportRegistry.abi.json.
 */
async function main(): Promise<void> {
  const { viem, networkName } = await network.create();
  const publicClient = await viem.getPublicClient();

  const chainId = await publicClient.getChainId();
  if (chainId !== EXPECTED_CHAIN_ID) {
    throw new Error(`Expected chain id ${EXPECTED_CHAIN_ID} on "${networkName}", got ${chainId}.`);
  }

  const [deployer, secondSubmitter] = await viem.getWalletClients();
  if (deployer === undefined || secondSubmitter === undefined) {
    throw new Error("Need at least two unlocked accounts on the node.");
  }
  const deployerAddress = getAddress(deployer.account.address);
  const submitterAddress = getAddress(secondSubmitter.account.address);

  console.log(`Deploying ReportRegistry to ${networkName} (chain ${chainId}) from ${deployerAddress}...`);
  const registry = await viem.deployContract("ReportRegistry");
  console.log(`ReportRegistry deployed at ${registry.address}`);

  const txHash = await registry.write.addSubmitter([submitterAddress]);
  await publicClient.waitForTransactionReceipt({ hash: txHash });
  console.log(`Added submitter ${submitterAddress}`);

  const artifact = await hre.artifacts.readArtifact("ReportRegistry");
  const localPath = await writeJson("local.json", {
    address: getAddress(registry.address),
    chainId,
    deployer: deployerAddress,
    submitters: [deployerAddress, submitterAddress],
  });
  const abiPath = await writeJson("ReportRegistry.abi.json", artifact.abi);
  console.log(`Wrote ${localPath}`);
  console.log(`Wrote ${abiPath}`);
}

await main();
