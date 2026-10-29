import assert from 'node:assert/strict'
import {
  assessFreshness,
  cashSession,
  displaySession,
  easterSunday,
  formatLastUpdateEt,
  heartbeatWithBuffer,
  nyseHolidays,
} from './src/marketHours.ts'

const utc = (y, m, d, h, min = 0) => Date.UTC(y, m - 1, d, h, min)

const easter = easterSunday(2026)
assert.equal(easter.getUTCFullYear(), 2026)
assert.equal(easter.getUTCMonth() + 1, 4)
assert.equal(easter.getUTCDate(), 5)

const holidays = nyseHolidays(2026)
assert.ok(holidays.has('2026-01-01'))
assert.ok(holidays.has('2026-04-03'))
assert.ok(holidays.has('2026-07-03'))
assert.ok(!holidays.has('2026-07-04'))

assert.equal(cashSession(utc(2026, 10, 29, 19, 7)), 'open')
assert.equal(cashSession(utc(2026, 10, 26, 12, 0)), 'pre')
assert.equal(cashSession(utc(2026, 10, 31, 16, 0)), 'closed')
assert.equal(displaySession(utc(2026, 11, 26, 20, 0), true), 'extended')

const { heartbeat, maxAge } = heartbeatWithBuffer(86400)
assert.equal(heartbeat, 86400)
assert.equal(maxAge, 87300)

const weekend = assessFreshness({
  marketHours: 'us_equities_24/5',
  heartbeat: 3600,
  updatedAt: Math.floor(utc(2026, 10, 30, 20, 0) / 1000),
  nowMs: utc(2026, 11, 1, 18, 0),
})
assert.equal(weekend.status, 'market_closed')
assert.match(weekend.message, /^Market closed, last update /)
assert.match(weekend.message, /ET$/)

const openStale = assessFreshness({
  marketHours: 'NYSE',
  heartbeat: 3600,
  updatedAt: Math.floor(utc(2026, 10, 29, 19, 7) / 1000) - 5000,
  nowMs: utc(2026, 10, 29, 19, 7),
})
assert.equal(openStale.status, 'stale')

const label = formatLastUpdateEt(Math.floor(utc(2026, 10, 30, 20, 0) / 1000))
assert.match(label, /^Fri /)
assert.match(label, /4:00 PM ET$/)

console.log('✅ market hours tests passed')
