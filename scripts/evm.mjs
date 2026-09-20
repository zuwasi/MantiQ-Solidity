import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { createHash } from "node:crypto";
import ganache from "ganache";
import solc from "solc";
import fc from "fast-check";
import {
  BrowserProvider,
  ContractFactory,
  parseEther,
  formatEther,
  ZeroAddress,
} from "ethers";

// No listening RPC, real wallet, or network fork. All accounts are disposable.
const settings = {
  optimizer: { enabled: true, runs: 200 },
  evmVersion: "shanghai",
  outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } },
};
const sources = Object.fromEntries(
  ["Escrow.sol", "DefectiveEscrow.sol", "TestActors.sol"].map((name) => [
    name,
    {
      content: readFileSync(
        new URL(`../contracts/${name}`, import.meta.url),
        "utf8",
      ),
    },
  ]),
);
const compiled = JSON.parse(
  solc.compile(JSON.stringify({ language: "Solidity", sources, settings })),
);
assert.deepEqual(
  (compiled.errors || []).filter((x) => x.severity === "error"),
  [],
  "Solidity compilation",
);
const checks = [];
const states = ["Funded", "Released", "Refunded"];
const amount = parseEther("10");
const start = 1800000000;
const deadline = start + 100;

async function environment() {
  const rpc = ganache.provider({
    logging: { quiet: true },
    chain: {
      chainId: 31337,
      hardfork: "shanghai",
      time: new Date(start * 1000),
    },
    miner: { timestampIncrement: 0 },
    wallet: { deterministic: true, totalAccounts: 4, defaultBalance: 1000 },
  });
  const provider = new BrowserProvider(rpc, undefined, { cacheTimeout: -1 });
  provider.pollingInterval = 10;
  const buyer = await provider.getSigner(0),
    seller = await provider.getSigner(1),
    stranger = await provider.getSigner(2);
  async function deploy(
    name = "Escrow",
    supplier = seller.address,
    due = deadline,
    value = amount,
  ) {
    const file =
      name === "Escrow"
        ? "Escrow.sol"
        : name === "DefectiveEscrow"
          ? "DefectiveEscrow.sol"
          : "TestActors.sol";
    const c = compiled.contracts[file][name];
    const factory = new ContractFactory(c.abi, c.evm.bytecode.object, buyer);
    const args = ["Escrow", "DefectiveEscrow"].includes(name)
      ? [supplier, due, { value }]
      : [];
    const contract = await factory.deploy(...args);
    await contract.waitForDeployment();
    return contract;
  }
  const balance = async (address) =>
    BigInt(
      await rpc.request({
        method: "eth_getBalance",
        params: [address, "latest"],
      }),
    );
  const time = async (timestamp) => {
    await rpc.request({ method: "evm_setTime", params: [timestamp * 1000] });
    await rpc.request({ method: "evm_mine", params: [] });
  };
  return {
    rpc,
    provider,
    buyer,
    seller,
    stranger,
    deploy,
    balance,
    time,
    close: async () => {
      provider.destroy();
      await rpc.disconnect();
    },
  };
}

async function execute(promise) {
  try {
    const receipt = await (await promise).wait();
    return { ok: true, hash: receipt.hash, receipt };
  } catch (error) {
    // Only a mined EVM revert counts as an expected rejection, never a transport error.
    if (error.code !== "CALL_EXCEPTION" || error.receipt?.status !== 0)
      throw error;
    return { ok: false, hash: error.receipt.hash, receipt: error.receipt };
  }
}

async function check(name, test) {
  const ctx = await environment();
  try {
    await test(ctx);
    checks.push({ name, passed: true });
    console.log(`PASS ${name}`);
  } finally {
    await ctx.close();
  }
}

const scenario = {
  amount: "10",
  units: "test ETH",
  precondition:
    "Buyer signs a call to an untrusted intermediary; supplier is fixed.",
};
for (const [variant, name] of [
  ["defective", "DefectiveEscrow"],
  ["fixed", "Escrow"],
]) {
  await check(`${variant}: identical intermediary call`, async (ctx) => {
    const escrow = await ctx.deploy(name),
      forwarder = await ctx.deploy("Intermediary");
    const before = await ctx.balance(ctx.seller.address);
    const outcome = await execute(
      forwarder.forward(await escrow.getAddress(), { gasLimit: 300000 }),
    );
    assert.equal(outcome.ok, variant === "defective");
    assert.equal(await escrow.state(), variant === "defective" ? 1n : 0n);
    assert.equal(
      await ctx.balance(await escrow.getAddress()),
      variant === "defective" ? 0n : amount,
    );
    const delta = (await ctx.balance(ctx.seller.address)) - before;
    assert.equal(delta, variant === "defective" ? amount : 0n);
    scenario[variant] = {
      state: states[Number(await escrow.state())],
      escrow: formatEther(await ctx.balance(await escrow.getAddress())),
      sellerDelta: formatEther(delta),
      txHash: outcome.hash,
      status: outcome.receipt.status,
    };
  });
}

await check("unauthorized direct release and refund rejected", async (ctx) => {
  const e = await ctx.deploy();
  assert.equal(
    (await execute(e.connect(ctx.stranger).release({ gasLimit: 300000 }))).ok,
    false,
  );
  await ctx.time(deadline);
  assert.equal(
    (await execute(e.connect(ctx.stranger).refund({ gasLimit: 300000 }))).ok,
    false,
  );
  assert.equal(await e.state(), 0n);
  assert.equal(await ctx.balance(await e.getAddress()), amount);
});

for (const offset of [-1, 0, 1]) {
  for (const method of ["release", "refund"]) {
    await check(
      `${method} at deadline ${offset >= 0 ? "+" : ""}${offset}`,
      async (ctx) => {
        const e = await ctx.deploy();
        await ctx.time(deadline + offset);
        const recipient =
          method === "release" ? ctx.seller.address : ctx.buyer.address;
        const before = await ctx.balance(recipient);
        const outcome = await execute(e[method]({ gasLimit: 300000 }));
        const allowed = method === "release" ? offset < 0 : offset >= 0;
        assert.equal(outcome.ok, allowed);
        const block = await ctx.provider.getBlock(outcome.receipt.blockNumber);
        assert.equal(
          block.timestamp,
          deadline + offset,
          "test executes on exact boundary",
        );
        assert.equal(
          await e.state(),
          allowed ? (method === "release" ? 1n : 2n) : 0n,
        );
        assert.equal(
          await ctx.balance(await e.getAddress()),
          allowed ? 0n : amount,
        );
        const gas = method === "refund" ? outcome.receipt.fee : 0n;
        assert.equal(
          (await ctx.balance(recipient)) - before + gas,
          allowed ? amount : 0n,
        );
        if (allowed) {
          assert.equal(
            (await execute(e[method]({ gasLimit: 300000 }))).ok,
            false,
            "cannot settle twice",
          );
          assert.equal(
            (
              await execute(
                e[method === "release" ? "refund" : "release"]({
                  gasLimit: 300000,
                }),
              )
            ).ok,
            false,
          );
        }
      },
    );
  }
}

await check("recipient failure rolls back state and funds", async (ctx) => {
  const receiver = await ctx.deploy("RejectingSupplier");
  const e = await ctx.deploy("Escrow", await receiver.getAddress());
  assert.equal((await execute(e.release({ gasLimit: 300000 }))).ok, false);
  assert.equal(await e.state(), 0n);
  assert.equal(await ctx.balance(await e.getAddress()), amount);
});

await check("invalid deployment terms rejected", async (ctx) => {
  for (const args of [
    [ZeroAddress, deadline, amount],
    [ctx.buyer.address, deadline, amount],
    [ctx.seller.address, start, amount],
    [ctx.seller.address, deadline, 0n],
  ]) {
    await assert.rejects(
      () => ctx.deploy("Escrow", ...args),
      (error) => error.code === "CALL_EXCEPTION",
    );
  }
});

// Stateful generated tests: asymmetric amounts, authorized/unauthorized calls,
// monotone times crossing the deadline, arbitrary action order, terminal absorption.
let generatedActions = 0,
  successfulSettlements = 0;
await fc.assert(
  fc.asyncProperty(
    fc.integer({ min: 1, max: 97 }),
    fc.array(
      fc.record({
        method: fc.constantFrom("release", "refund"),
        authorized: fc.boolean(),
        advance: fc.integer({ min: 0, max: 55 }),
      }),
      { minLength: 2, maxLength: 8 },
    ),
    async (value, actions) => {
      const ctx = await environment();
      try {
        const funded = BigInt(value) * 1000000000000n;
        const e = await ctx.deploy(
          "Escrow",
          ctx.seller.address,
          deadline,
          funded,
        );
        let state = 0,
          now = start,
          paid = 0n;
        // Guarantee one eventual valid settlement per sequence, not just rejections.
        const sequence = [
          ...actions,
          { method: "refund", authorized: true, advance: 200 },
        ];
        for (const action of sequence) {
          now += action.advance;
          await ctx.time(now);
          const expected =
            state === 0 &&
            action.authorized &&
            (action.method === "release" ? now < deadline : now >= deadline);
          const outcome = await execute(
            e
              .connect(action.authorized ? ctx.buyer : ctx.stranger)
              [action.method]({ gasLimit: 300000 }),
          );
          assert.equal(outcome.ok, expected);
          if (expected) {
            state = action.method === "release" ? 1 : 2;
            paid += funded;
            successfulSettlements++;
          }
          assert.equal(Number(await e.state()), state);
          assert.equal(
            (await ctx.balance(await e.getAddress())) + paid,
            funded,
          );
          assert.ok(paid <= funded);
          generatedActions++;
        }
        assert.notEqual(state, 0);
      } finally {
        await ctx.close();
      }
    },
  ),
  { numRuns: 20, seed: 20260920, endOnFailure: false },
);
checks.push({
  name: "20 generated transaction sequences: state, conservation, single settlement",
  passed: true,
});

const artifacts = Object.fromEntries(
  Object.entries(compiled.contracts).flatMap(([file, contracts]) =>
    Object.entries(contracts)
      .filter(([, c]) => c.evm.bytecode.object)
      .map(([name, c]) => [
        name,
        {
          source: file,
          bytecodeSha256: createHash("sha256")
            .update(c.evm.bytecode.object)
            .digest("hex"),
        },
      ]),
  ),
);
const evidence = {
  compiler: solc.version(),
  engine: "Ganache 7.9.2, in-process EVM",
  settings,
  checks,
  scenario,
  generated: {
    seed: 20260920,
    sequences: 20,
    actions: generatedActions,
    successfulSettlements,
  },
  artifacts,
};
const output = resolve(process.argv[2] || "runs/evm.json");
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(evidence, null, 2));
console.log(
  `PASS ${checks.length} checks; ${generatedActions} generated actions. Evidence: ${output}`,
);
