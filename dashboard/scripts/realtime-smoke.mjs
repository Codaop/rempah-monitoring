// Realtime smoke test: log in, subscribe to sensor_logs INSERTS, insert a
// row, and assert the realtime event arrives. Run with:
//   SUPABASE_URL=... SUPABASE_ANON_KEY=... EMAIL=... PASSWORD=... \
//   node --experimental-websocket scripts/realtime-smoke.mjs
import { createClient } from '@supabase/supabase-js'

const url = process.env.SUPABASE_URL
const anon = process.env.SUPABASE_ANON_KEY
const email = process.env.EMAIL
const password = process.env.PASSWORD

for (const [name, v] of Object.entries({ SUPABASE_URL: url, SUPABASE_ANON_KEY: anon, EMAIL: email, PASSWORD: password })) {
  if (!v) {
    console.error(`missing env ${name}`)
    process.exit(1)
  }
}

const client = createClient(url, anon, { auth: { persistSession: false } })

const { error } = await client.auth.signInWithPassword({ email, password })
if (error) {
  console.error('login failed:', error.message)
  process.exit(1)
}
console.log('login OK for', email, '(producer_id', '0d0d0000-0000-4000-8000-000000000001)')

const received = new Promise((resolve, reject) => {
  const timeout = setTimeout(() => reject(new Error('realtime timeout (15s)')), 15000)
  client
    .channel('smoke-test')
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'sensor_logs' }, (payload) => {
      clearTimeout(timeout)
      console.log('realtime INSERT received:', payload.new.boiler_temp_c, '°C at', payload.new.ts)
      resolve(payload.new)
    })
    .subscribe()
})

await new Promise((r) => setTimeout(r, 1500))
const { error: insErr } = await client
  .from('sensor_logs')
  .insert({
    producer_id: '0d0d0000-0000-4000-8000-000000000001',
    device_id: '1a1a0000-0000-4000-8000-000000000001',
    boiler_temp_c: 88.5,
    gas_pressure_kpa: 3.0,
    water_level: 64.0,
    drip_count: 5,
    flame_lit: true,
  })
if (insErr) console.error('insert error:', insErr.message)

await received
console.log('REALTIME SMOKE TEST PASSED')
process.exit(0)