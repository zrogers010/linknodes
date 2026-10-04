import { useState } from 'react'
import { ProductLayout } from '../../components/ProductLayout'

export function VRFPage() {
  const [numWords, setNumWords] = useState(1)
  const [mockRandoms, setMockRandoms] = useState<string[]>([])
  
  const generateMockRandoms = () => {
    const randoms = Array.from({ length: numWords }, () => 
      '0x' + Array.from({ length: 64 }, () => 
        Math.floor(Math.random() * 16).toString(16)
      ).join('')
    )
    setMockRandoms(randoms)
  }
  
  return (
    <ProductLayout
      icon="🎲"
      title="Chainlink VRF"
      tagline="Verifiable Random Function"
      status="preview"
      description={
        <>
          Generate provably fair and tamper-proof random numbers on-chain. Perfect for NFT mints, gaming, lotteries, and any application requiring cryptographically secure randomness with on-chain verification.
        </>
      }
    >
      <div className="p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          {/* Feature cards */}
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">✅</div>
              <h3 className="mb-1 text-sm font-bold text-white">Cryptographic Proof</h3>
              <p className="text-xs text-slate-400">
                Each random number includes a cryptographic proof verifiable on-chain
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">🔒</div>
              <h3 className="mb-1 text-sm font-bold text-white">Tamper-proof</h3>
              <p className="text-xs text-slate-400">
                No oracle, miner, or user can manipulate the outcome — guaranteed fairness
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">⚡</div>
              <h3 className="mb-1 text-sm font-bold text-white">Two Request Methods</h3>
              <p className="text-xs text-slate-400">
                Choose between subscription-based or direct funding for maximum flexibility
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">📈</div>
              <h3 className="mb-1 text-sm font-bold text-white">Battle-tested</h3>
              <p className="text-xs text-slate-400">
                Millions of random numbers generated across thousands of applications
              </p>
            </div>
          </div>

          {/* Interactive section */}
          <div className="rounded-2xl border border-ink-700 bg-ink-900">
            <div className="border-b border-ink-700 p-5">
              <h2 className="text-lg font-bold text-white">Randomness Generator (Preview)</h2>
              <p className="mt-1 text-sm text-slate-400">
                Simulate VRF random number generation. Full sandbox with testnet integration coming soon.
              </p>
            </div>
            
            <div className="p-5">
              <div className="mb-6 grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Number of Random Values
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={numWords}
                    onChange={(e) => setNumWords(Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
                    className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-500"
                  />
                  <p className="mt-1.5 text-xs text-slate-500">
                    Request 1-10 random words in a single call
                  </p>
                </div>
                
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Callback Gas Limit
                  </label>
                  <select className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-500">
                    <option>100,000 gas</option>
                    <option>200,000 gas</option>
                    <option>500,000 gas</option>
                    <option>1,000,000 gas</option>
                  </select>
                  <p className="mt-1.5 text-xs text-slate-500">
                    Gas limit for your fulfillment callback
                  </p>
                </div>
              </div>

              <button
                onClick={generateMockRandoms}
                className="w-full rounded-lg bg-accent-500 py-3 font-semibold text-white transition-colors hover:bg-accent-600 sm:w-auto sm:px-8"
              >
                Generate Random Numbers
              </button>

              {mockRandoms.length > 0 && (
                <div className="mt-5 rounded-lg border border-ink-700 bg-ink-950 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Generated Random Values (Preview Only)
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {mockRandoms.map((random, idx) => (
                      <div key={idx} className="flex items-start gap-3">
                        <span className="shrink-0 font-mono text-xs text-slate-500">
                          [{idx}]
                        </span>
                        <code className="min-w-0 flex-1 break-all font-mono text-xs text-accent-300">
                          {random}
                        </code>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 rounded-lg border border-sky-500/30 bg-sky-500/5 p-3">
                    <div className="flex items-start gap-2 text-xs">
                      <svg className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                      <div className="text-slate-400">
                        <div className="font-semibold text-sky-400">Preview only</div>
                        <div className="mt-1">
                          These are client-side mock values for demonstration. A live VRF testnet sandbox with real on-chain verification is coming soon.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Integration example */}
            <div className="border-t border-ink-700 bg-ink-950 p-5">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Solidity Integration Example
              </h3>
              <pre className="overflow-x-auto rounded-lg bg-ink-900 p-4 font-mono text-xs text-slate-300">
{`// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/vrf/VRFConsumerBaseV2.sol";

contract RandomNumberConsumer is VRFConsumerBaseV2 {
    uint256[] public randomWords;
    uint256 public requestId;
    
    function requestRandomWords() external {
        requestId = COORDINATOR.requestRandomWords(
            keyHash,
            subscriptionId,
            requestConfirmations,
            callbackGasLimit,
            numWords
        );
    }
    
    function fulfillRandomWords(
        uint256 _requestId,
        uint256[] memory _randomWords
    ) internal override {
        randomWords = _randomWords;
        // Use your random numbers here
    }
}`}
              </pre>
            </div>
          </div>

          {/* Use cases */}
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-bold text-white">Popular Use Cases</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎨</span>
                  <span>NFT Minting</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Fair distribution of rare traits. Generate unpredictable metadata at mint time that no one can game.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎮</span>
                  <span>Gaming</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Loot drops, enemy spawns, critical hits — provably fair randomness for blockchain games.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎰</span>
                  <span>Lotteries & Raffles</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Pick verifiably random winners. Users can cryptographically prove the outcome was fair.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎯</span>
                  <span>Random Assignment</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Assign tasks, seats, or resources randomly without bias. Perfect for DAOs and governance.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🔀</span>
                  <span>Shuffling</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Randomize order in card games, battle queues, or any system requiring fair shuffling.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🌟</span>
                  <span>Surprise Mechanics</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Create engaging, unpredictable experiences while maintaining cryptographic fairness.
                </p>
              </div>
            </div>
          </div>

          {/* VRF versions comparison */}
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-bold text-white">VRF v2 vs VRF v2.5</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">VRF v2</h3>
                  <span className="rounded-full border border-ink-600 bg-ink-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Stable
                  </span>
                </div>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Subscription-based model</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Multiple contracts per subscription</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Most chains supported</span>
                  </li>
                </ul>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">VRF v2.5</h3>
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                    Latest
                  </span>
                </div>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Subscription + direct funding</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Improved gas efficiency</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>Native LINK or wrapped LINK</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Resources */}
          <div className="mt-8 rounded-xl border border-accent-500/30 bg-accent-500/5 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">Coming Soon: Live VRF Testnet Sandbox</h3>
            <p className="mb-4 text-sm text-slate-400">
              We're building a full VRF sandbox with testnet integration, real random number generation, and proof verification. In the meantime, explore the official resources:
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://docs.chain.link/vrf"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                VRF Documentation
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
              <a
                href="https://vrf.chain.link"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                VRF Subscription Manager
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
