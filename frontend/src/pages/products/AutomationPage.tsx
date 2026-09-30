import { useState } from 'react'
import { ProductLayout } from '../../components/ProductLayout'

const AUTOMATION_TYPES = [
  { id: 'time', name: 'Time-based', icon: '⏰', description: 'Execute at specific times or intervals' },
  { id: 'custom', name: 'Custom Logic', icon: '🔍', description: 'Trigger based on custom conditions' },
  { id: 'log', name: 'Log Triggers', icon: '📋', description: 'React to emitted contract events' },
]

const EXAMPLE_CONDITIONS = [
  {
    name: 'Liquidation Monitor',
    type: 'custom',
    description: 'Monitor lending positions and trigger liquidations when health factor drops below threshold',
    code: 'healthFactor < 1.0',
  },
  {
    name: 'NFT Reveal',
    type: 'time',
    description: 'Automatically reveal NFT metadata 24 hours after mint',
    code: 'block.timestamp >= revealTime',
  },
  {
    name: 'Yield Harvesting',
    type: 'custom',
    description: 'Compound rewards when accumulated yield exceeds gas costs',
    code: 'pendingRewards > gasThreshold',
  },
]

export function AutomationPage() {
  const [selectedType, setSelectedType] = useState('custom')
  const [condition, setCondition] = useState('return (block.timestamp % 3600 == 0);')
  
  return (
    <ProductLayout
      icon="🤖"
      title="Chainlink Automation"
      tagline="Decentralized Smart Contract Automation"
      status="preview"
      description={
        <>
          Trigger smart contract functions automatically using decentralized keepers. Execute time-based tasks, monitor custom conditions, and react to events — all without running your own infrastructure.
        </>
      }
    >
      <div className="p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          {/* Automation types */}
          <div className="mb-8 grid gap-4 sm:grid-cols-3">
            {AUTOMATION_TYPES.map((type) => (
              <button
                key={type.id}
                onClick={() => setSelectedType(type.id)}
                className={`rounded-xl border p-5 text-left transition-all ${
                  selectedType === type.id
                    ? 'border-accent-500 bg-accent-500/10'
                    : 'border-ink-700 bg-ink-900 hover:border-ink-600'
                }`}
              >
                <div className="mb-2 text-2xl">{type.icon}</div>
                <h3 className="mb-1 text-sm font-bold text-white">{type.name}</h3>
                <p className="text-xs text-slate-400">{type.description}</p>
              </button>
            ))}
          </div>

          {/* Interactive builder */}
          <div className="rounded-2xl border border-ink-700 bg-ink-900">
            <div className="border-b border-ink-700 p-5">
              <h2 className="text-lg font-bold text-white">Automation Builder (Preview)</h2>
              <p className="mt-1 text-sm text-slate-400">
                Design automation logic. Full sandbox with testnet registration coming soon.
              </p>
            </div>
            
            <div className="p-5">
              <div className="mb-5">
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Upkeep Condition (Solidity)
                </label>
                <textarea
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  className="h-32 w-full rounded-lg border border-ink-600 bg-ink-950 p-4 font-mono text-sm text-slate-200 outline-none focus:border-accent-500"
                  placeholder="function checkUpkeep(bytes calldata) external view returns (bool upkeepNeeded, bytes memory) {
  // Your condition logic here
}"
                />
                <p className="mt-2 text-xs text-slate-500">
                  This function is called off-chain by Chainlink nodes. When it returns true, your performUpkeep function executes on-chain.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Target Contract
                  </label>
                  <input
                    type="text"
                    placeholder="0x..."
                    className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 font-mono text-sm text-slate-200 outline-none focus:border-accent-500"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Check Interval
                  </label>
                  <select className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-500">
                    <option>Every block (~12s)</option>
                    <option>Every minute</option>
                    <option>Every 5 minutes</option>
                    <option>Every hour</option>
                  </select>
                </div>
              </div>

              <div className="mt-5 rounded-lg border border-ink-700 bg-ink-950 p-4">
                <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  How it works
                </h3>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">1</div>
                    <div className="text-sm text-slate-400">
                      <span className="font-semibold text-slate-300">Off-chain monitoring:</span> Chainlink nodes call your <code className="rounded bg-ink-800 px-1 py-0.5 text-accent-300">checkUpkeep()</code> function at regular intervals
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">2</div>
                    <div className="text-sm text-slate-400">
                      <span className="font-semibold text-slate-300">Condition evaluation:</span> When your logic returns true, the network prepares to execute
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">3</div>
                    <div className="text-sm text-slate-400">
                      <span className="font-semibold text-slate-300">On-chain execution:</span> A node calls <code className="rounded bg-ink-800 px-1 py-0.5 text-accent-300">performUpkeep()</code> with the provided data
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">4</div>
                    <div className="text-sm text-slate-400">
                      <span className="font-semibold text-slate-300">Gas optimization:</span> Your contract pays gas + premium only when upkeep is performed
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Integration example */}
            <div className="border-t border-ink-700 bg-ink-950 p-5">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Solidity Integration Example
              </h3>
              <pre className="overflow-x-auto rounded-lg bg-ink-900 p-4 font-mono text-xs text-slate-300">
{`// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/automation/AutomationCompatible.sol";

contract MyAutomatedContract is AutomationCompatibleInterface {
    uint256 public counter;
    uint256 public lastTimeStamp;
    uint256 public immutable interval;
    
    constructor(uint256 updateInterval) {
        interval = updateInterval;
        lastTimeStamp = block.timestamp;
    }
    
    function checkUpkeep(bytes calldata) 
        external 
        view 
        override 
        returns (bool upkeepNeeded, bytes memory) 
    {
        upkeepNeeded = (block.timestamp - lastTimeStamp) > interval;
    }
    
    function performUpkeep(bytes calldata) external override {
        if ((block.timestamp - lastTimeStamp) > interval) {
            lastTimeStamp = block.timestamp;
            counter = counter + 1;
            // Your automation logic here
        }
    }
}`}
              </pre>
            </div>
          </div>

          {/* Example use cases */}
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-bold text-white">Example Automation Strategies</h2>
            <div className="space-y-3">
              {EXAMPLE_CONDITIONS.map((example) => (
                <div key={example.name} className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                  <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-white">{example.name}</h3>
                        <span className="rounded-full border border-ink-600 bg-ink-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          {AUTOMATION_TYPES.find(t => t.id === example.type)?.name}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{example.description}</p>
                    </div>
                  </div>
                  <div className="rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-xs text-accent-300">
                    {example.code}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Popular use cases grid */}
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-bold text-white">What You Can Automate</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>💰</span>
                  <span>DeFi Strategies</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Auto-compound yields, rebalance portfolios, trigger stop-losses, and manage positions without manual intervention.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>⚖️</span>
                  <span>Liquidations</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Monitor lending protocols and automatically liquidate undercollateralized positions as they reach thresholds.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎨</span>
                  <span>NFT Mechanics</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Scheduled reveals, dynamic trait updates, auction endings, and time-based NFT state changes.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🗳️</span>
                  <span>DAO Operations</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Execute passed proposals, distribute rewards, update parameters, and run scheduled governance tasks.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎮</span>
                  <span>Gaming Logic</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Turn-based mechanics, scheduled events, reward distributions, and automated game state management.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>⚡</span>
                  <span>System Maintenance</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Clear expired data, reset counters, clean up storage, and perform routine contract maintenance tasks.
                </p>
              </div>
            </div>
          </div>

          {/* Features comparison */}
          <div className="mt-8 rounded-2xl border border-ink-700 bg-ink-900 p-6">
            <h2 className="mb-4 text-lg font-bold text-white">Why Chainlink Automation?</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="text-sm font-semibold text-white">No infrastructure</div>
                    <div className="text-xs text-slate-400">No servers, no DevOps, no maintenance — just register your contract</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="text-sm font-semibold text-white">Highly reliable</div>
                    <div className="text-xs text-slate-400">Decentralized node network with automatic failover and redundancy</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="text-sm font-semibold text-white">Gas optimized</div>
                    <div className="text-xs text-slate-400">Pay only when tasks execute, with competitive gas premiums</div>
                  </div>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="text-sm font-semibold text-white">Decentralized</div>
                    <div className="text-xs text-slate-400">No single point of failure — trustless execution by Chainlink nodes</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="text-sm font-semibold text-white">Battle-tested</div>
                    <div className="text-xs text-slate-400">Billions in TVL secured, millions of upkeeps performed across chains</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <div className="text-sm font-semibold text-white">Flexible triggers</div>
                    <div className="text-xs text-slate-400">Time-based, custom logic, or event-driven — choose what fits your use case</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Resources */}
          <div className="mt-8 rounded-xl border border-accent-500/30 bg-accent-500/5 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">Coming Soon: Live Automation Testnet Sandbox</h3>
            <p className="mb-4 text-sm text-slate-400">
              We're building a complete Automation sandbox with testnet registration, upkeep monitoring, and execution tracking. In the meantime, explore the official resources:
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://docs.chain.link/chainlink-automation"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                Automation Documentation
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
              <a
                href="https://automation.chain.link"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                Automation Dashboard
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </ProductLayout>
  )
}
