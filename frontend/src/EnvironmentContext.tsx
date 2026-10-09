import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import type { Registry } from './types'
import { apiUrl } from './config'

interface EnvironmentContextType {
  environment: 'mainnet' | 'testnet'
  setEnvironment: (env: 'mainnet' | 'testnet') => void
  registry: Registry | null
  registryError: string | null
}

const EnvironmentContext = createContext<EnvironmentContextType | null>(null)

export function useEnvironment() {
  const context = useContext(EnvironmentContext)
  if (!context) {
    throw new Error('useEnvironment must be used within EnvironmentProvider')
  }
  return context
}

export function EnvironmentProvider({ children }: { children: ReactNode }) {
  const [environment, setEnvironment] = useState<'mainnet' | 'testnet'>('mainnet')
  const [registryMainnet, setRegistryMainnet] = useState<Registry | null>(null)
  const [registryTestnet, setRegistryTestnet] = useState<Registry | null>(null)
  const [registryError, setRegistryError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetch(apiUrl('/v1/registry', 'mainnet')).then(r => r.json()),
      fetch(apiUrl('/v1/registry', 'testnet')).then(r => r.json()),
    ])
      .then(([mainnet, testnet]) => {
        setRegistryMainnet(mainnet)
        setRegistryTestnet(testnet)
      })
      .catch((e) => setRegistryError(String(e)))
  }, [])

  const registry = environment === 'testnet' ? registryTestnet : registryMainnet

  return (
    <EnvironmentContext.Provider value={{ environment, setEnvironment, registry, registryError }}>
      {children}
    </EnvironmentContext.Provider>
  )
}
