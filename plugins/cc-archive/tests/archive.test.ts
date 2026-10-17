import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

const SID = 'abcd1234-0000-0000-0000-000000000000'

// Stands in for the session and the cc-archive CLI: records each call and answers like the CLI would.
function fakeCli(on: On, answer: string) {
  const calls: string[][] = []
  on('session.id', () => ({ value: SID }))
  on('process.run', (_$, e) => {
    calls.push([...e.argv])
    return { value: { exitCode: 0, stdout: answer, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  return calls
}

test('/archive with no ID marks the current session', async ($, on) => {
  const calls = fakeCli(on, 'abcd1234 is open: it will be archived when it closes')
  const ran = await $.command.run({ command: 'archive' })
  expect(calls).toEqual([['cc-archive', SID]])
  expect(ran.text).toContain('when it closes')
})

test('/archive ID and /unarchive ID pass the ID through', async ($, on) => {
  const calls = fakeCli(on, 'done')
  await $.command.run({ command: 'archive', args: '21ddae63' })
  await $.command.run({ command: 'unarchive', args: '21ddae63' })
  await $.command.run({ command: 'unarchive', args: 'list' })
  expect(calls).toEqual([['cc-archive', '21ddae63'], ['cc-archive', '-r', '21ddae63'], ['cc-archive', '-l']])
})

test('a missing CLI is reported, not thrown', async ($, on) => {
  on('session.id', () => ({ value: SID }))
  on('process.run', () => {
    throw new Error('ENOENT')
  })
  const ran = await $.command.run({ command: 'archive', args: 'list' })
  expect(ran.text).toContain('install.sh')
})
