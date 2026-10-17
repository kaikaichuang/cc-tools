import type { EngineInterface, Register } from 'claude-code'

// The plugin only drives the cc-archive CLI (cc-tools/bin), which does the moving.
const CLI = 'cc-archive'
const PENDING_NOTE = 'archived after this session closes (/unarchive to cancel)'

async function cli($: EngineInterface, args: string[]): Promise<string> {
  try {
    const { stdout, stderr } = await $.process.run([CLI, ...args])
    return (stdout + stderr).trim() || '(nothing to show)'
  } catch {
    return `${CLI} is not installed: clone cc-tools and run its install.sh`
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'archive',
      description: 'Archive this session when it closes, or another session now',
      argumentHint: '[ID | list]',
    })
    await $.command.register({
      name: 'unarchive',
      description: 'Cancel archiving this session, or restore an archived one',
      argumentHint: '[ID | list]',
    })
    // Sessions marked by /archive are moved here, once the claude that held them has exited,
    // rather than by a process left running after exit. cc-archive does the same on every run.
    await cli($, ['--pending'])
    return next(e)
  })

  // An open session cannot be moved (claude keeps writing to it), so the CLI only marks it.
  on('command.run', { command: 'archive' }, async ($, e) => {
    const arg = (e.args ?? '').trim()
    if (arg === 'list') return { text: await cli($, []) }
    const sid = await $.session.id()
    const target = arg === '' ? sid : arg
    const text = await cli($, [target])
    if (sid.startsWith(target) && text.includes('when it closes')) $.ui.status(PENDING_NOTE)
    return { text }
  })

  on('command.run', { command: 'unarchive' }, async ($, e) => {
    const arg = (e.args ?? '').trim()
    if (arg === 'list') return { text: await cli($, ['-l']) }
    const sid = await $.session.id()
    const target = arg === '' ? sid : arg
    const text = await cli($, ['-r', target])
    if (sid.startsWith(target) && text.includes('no longer')) $.ui.status(undefined)
    return { text }
  })
}
