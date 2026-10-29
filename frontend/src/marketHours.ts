/**
 * NYSE / US-equities session calendar (mirrors backend/market_hours.py).
 *
 * Session badges are calculated by LinkNodes from the NYSE cash-market
 * calendar and US market holidays. They are not an oracle marketStatus value.
 *
 * Chainlink Streams marketStatus (never derived from timestamps):
 *   0 Unknown, 1 Pre, 2 Regular, 3 Post, 4 Overnight, 5 Closed
 * https://docs.chain.link/data-streams/market-hours
 * https://docs.chain.link/data-streams/rwa-streams/24-5-us-equities-user-guide
 */

export const STALE_BUFFER_S = 900
export const DEFAULT_HEARTBEAT_S = 3600

export const SESSION_OPEN = 'open'
export const SESSION_PRE = 'pre'
export const SESSION_POST = 'post'
export const SESSION_OVERNIGHT = 'overnight'
export const SESSION_CLOSED = 'closed'
export const SESSION_EXTENDED = 'extended'

export type MarketSession =
  | typeof SESSION_OPEN
  | typeof SESSION_PRE
  | typeof SESSION_POST
  | typeof SESSION_OVERNIGHT
  | typeof SESSION_CLOSED
  | typeof SESSION_EXTENDED

const ALWAYS_ON = new Set(['crypto', '24/7', '247'])
const HOURS_24_5 = new Set([
  'us_equities_24/5',
  '24/5',
  'forex',
  'forex_brl',
  'forex_php',
  'forex_krw',
  'forex_inr',
  'forex_ars',
  'forex_idr',
  'forex_ngn',
  'forex_cop',
  'forex_ils',
  'forex_ghs',
  'forex_kes',
  'forex_xof',
  'precious_metals',
  'wti',
])
const HOURS_CASH = new Set(['nyse', 'lse', 'euronext_milan'])
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

function nthWeekday(year: number, month: number, weekday: number, n: number): Date {
  // weekday: Mon=0 … Sun=6. JS getUTCDay: Sun=0 … Sat=6.
  const first = new Date(Date.UTC(year, month - 1, 1))
  const jsWeekday = (weekday + 1) % 7
  const firstOffset = (jsWeekday - first.getUTCDay() + 7) % 7
  return new Date(Date.UTC(year, month - 1, 1 + firstOffset + 7 * (n - 1)))
}

function lastWeekday(year: number, month: number, weekday: number): Date {
  const last = new Date(Date.UTC(year, month, 0))
  const jsWeekday = (weekday + 1) % 7
  const offset = (last.getUTCDay() - jsWeekday + 7) % 7
  return new Date(Date.UTC(year, month - 1, last.getUTCDate() - offset))
}

export function easterSunday(year: number): Date {
  const a = year % 19
  const b = Math.floor(year / 100)
  const c = year % 100
  const d = Math.floor(b / 4)
  const e = b % 4
  const f = Math.floor((b + 8) / 25)
  const g = Math.floor((b - f + 1) / 3)
  const h = (19 * a + b - d - g + 15) % 30
  const i = Math.floor(c / 4)
  const k = c % 4
  const l = (32 + 2 * e + 2 * i - h - k) % 7
  const m = Math.floor((a + 11 * h + 22 * l) / 451)
  const month = Math.floor((h + l - 7 * m + 114) / 31)
  const day = ((h + l - 7 * m + 114) % 31) + 1
  return new Date(Date.UTC(year, month - 1, day))
}

function observe(d: Date): Date {
  const wd = d.getUTCDay()
  if (wd === 6) return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - 1))
  if (wd === 0) return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + 1))
  return d
}

function dateKey(d: Date): string {
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`
}

export function nyseHolidays(year: number): Set<string> {
  const easter = easterSunday(year)
  const goodFriday = new Date(Date.UTC(easter.getUTCFullYear(), easter.getUTCMonth(), easter.getUTCDate() - 2))
  const days = [
    observe(new Date(Date.UTC(year, 0, 1))),
    nthWeekday(year, 1, 0, 3),
    nthWeekday(year, 2, 0, 3),
    goodFriday,
    lastWeekday(year, 5, 0),
    observe(new Date(Date.UTC(year, 5, 19))),
    observe(new Date(Date.UTC(year, 6, 4))),
    nthWeekday(year, 9, 0, 1),
    nthWeekday(year, 11, 3, 4),
    observe(new Date(Date.UTC(year, 11, 25))),
  ]
  return new Set(days.map(dateKey))
}

export function isUsEasternDst(utcMs: number): boolean {
  const utc = new Date(utcMs)
  const year = utc.getUTCFullYear()
  const start = nthWeekday(year, 3, 6, 2).getTime() + 7 * 3600 * 1000
  const end = nthWeekday(year, 11, 6, 1).getTime() + 6 * 3600 * 1000
  return utcMs >= start && utcMs < end
}

export function toEasternParts(utcMs: number): {
  year: number
  month: number
  day: number
  hour: number
  minute: number
  weekday: number
  dateKey: string
} {
  const offsetH = isUsEasternDst(utcMs) ? -4 : -5
  const et = new Date(utcMs + offsetH * 3600 * 1000)
  return {
    year: et.getUTCFullYear(),
    month: et.getUTCMonth() + 1,
    day: et.getUTCDate(),
    hour: et.getUTCHours(),
    minute: et.getUTCMinutes(),
    weekday: (et.getUTCDay() + 6) % 7, // Mon=0
    dateKey: dateKey(et),
  }
}

function normHours(marketHours?: string | null): string {
  return (marketHours || '').trim().toLowerCase()
}

export function isAlwaysOnHours(marketHours?: string | null): boolean {
  return ALWAYS_ON.has(normHours(marketHours))
}

export function isSessionBasedHours(marketHours?: string | null): boolean {
  const hours = normHours(marketHours)
  if (!hours || ALWAYS_ON.has(hours)) return false
  return HOURS_24_5.has(hours) || HOURS_CASH.has(hours) || hours.startsWith('forex')
}

export function cashSession(nowMs: number = Date.now()): MarketSession {
  const et = toEasternParts(nowMs)
  let holidays = nyseHolidays(et.year)
  if (et.month === 1 && et.day <= 2) {
    holidays = new Set([...holidays, ...nyseHolidays(et.year - 1)])
  }
  if (et.month === 12 && et.day >= 30) {
    holidays = new Set([...holidays, ...nyseHolidays(et.year + 1)])
  }
  if (holidays.has(et.dateKey)) return SESSION_CLOSED

  const minutes = et.hour * 60 + et.minute
  if (et.weekday === 5) return SESSION_CLOSED
  if (et.weekday === 6) return minutes >= 18 * 60 ? SESSION_OVERNIGHT : SESSION_CLOSED
  if (et.weekday === 4 && minutes >= 20 * 60) return SESSION_CLOSED
  if (minutes >= 9 * 60 + 30 && minutes < 16 * 60) return SESSION_OPEN
  if (minutes >= 4 * 60 && minutes < 9 * 60 + 30) return SESSION_PRE
  if (minutes >= 16 * 60 && minutes < 20 * 60) return SESSION_POST
  return SESSION_OVERNIGHT
}

export function displaySession(nowMs: number = Date.now(), is247 = false): MarketSession {
  const session = cashSession(nowMs)
  if (session === SESSION_CLOSED && is247) return SESSION_EXTENDED
  return session
}

export function feedIsUpdating(
  marketHours: string | null | undefined,
  session: MarketSession,
  is247 = false,
): boolean {
  if (is247 || isAlwaysOnHours(marketHours)) return true
  const hours = normHours(marketHours)
  if (HOURS_CASH.has(hours)) return session === SESSION_OPEN
  if (HOURS_24_5.has(hours) || hours.startsWith('forex')) {
    return (
      session === SESSION_OPEN ||
      session === SESSION_PRE ||
      session === SESSION_POST ||
      session === SESSION_OVERNIGHT
    )
  }
  return true
}

export function formatLastUpdateEt(updatedAt?: number | null): string {
  if (!updatedAt) return 'unknown time'
  const et = toEasternParts(updatedAt * 1000)
  const hour12 = et.hour % 12 || 12
  const ampm = et.hour < 12 ? 'AM' : 'PM'
  return `${WEEKDAYS[et.weekday]} ${hour12}:${String(et.minute).padStart(2, '0')} ${ampm} ET`
}

export function heartbeatWithBuffer(heartbeat?: number | null): { heartbeat: number; maxAge: number } {
  const hb = heartbeat && heartbeat > 0 ? heartbeat : DEFAULT_HEARTBEAT_S
  return { heartbeat: hb, maxAge: hb + STALE_BUFFER_S }
}

export type FreshnessStatus = 'fresh' | 'stale' | 'market_closed' | 'unknown'

export interface Freshness {
  status: FreshnessStatus
  heartbeat_seconds: number
  max_age_seconds: number
  age_seconds: number | null
  session: MarketSession
  session_source: 'linknodes'
  message: string
}

export function assessFreshness(opts: {
  marketHours?: string | null
  heartbeat?: number | null
  updatedAt?: number | null
  nowMs?: number
  is247?: boolean
}): Freshness {
  const nowMs = opts.nowMs ?? Date.now()
  const { heartbeat, maxAge } = heartbeatWithBuffer(opts.heartbeat)
  const session = displaySession(nowMs, opts.is247)
  const cash = cashSession(nowMs)
  const age = opts.updatedAt != null ? Math.max(0, Math.floor(nowMs / 1000) - opts.updatedAt) : null
  const updating = feedIsUpdating(opts.marketHours, cash, opts.is247)
  const lastEt = formatLastUpdateEt(opts.updatedAt)

  if (!updating) {
    return {
      status: 'market_closed',
      heartbeat_seconds: heartbeat,
      max_age_seconds: maxAge,
      age_seconds: age,
      session,
      session_source: 'linknodes',
      message: `Market closed, last update ${lastEt}`,
    }
  }

  let status: FreshnessStatus = 'unknown'
  let message = 'No update timestamp'
  if (age != null) {
    if (age > maxAge) {
      status = 'stale'
      message = `Stale (${age}s old, heartbeat ${heartbeat}s + ${STALE_BUFFER_S}s)`
    } else {
      status = 'fresh'
      message = `Updated ${lastEt}`
    }
  }

  return {
    status,
    heartbeat_seconds: heartbeat,
    max_age_seconds: maxAge,
    age_seconds: age,
    session,
    session_source: 'linknodes',
    message,
  }
}

export const SESSION_LABEL: Record<MarketSession, string> = {
  open: 'Open',
  pre: 'Pre',
  post: 'Post',
  overnight: 'Overnight',
  closed: 'Closed',
  extended: 'Extended',
}

export const SESSION_STYLE: Record<MarketSession, string> = {
  open: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  pre: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
  post: 'border-violet-500/40 bg-violet-500/10 text-violet-300',
  overnight: 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300',
  closed: 'border-ink-600 bg-ink-800 text-slate-400',
  extended: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
}
