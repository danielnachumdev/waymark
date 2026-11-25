import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type CalendarFeedStatus } from '../api'
import { useConfirm } from '../lib/dialogs'
import { useToast } from '../lib/toast'
import { useAction } from '../lib/useAction'
import { Alert } from './Feedback'
import { Icon } from './Icon'
import { SecretReveal } from './SecretReveal'
import { Section } from './Section'

export function calendarFeedUrl(token: string): string {
  return `${window.location.origin}/api/public/calendar/${token}.ics`
}

export function calendarFeedRedactedUrl(token: string): string {
  return `${window.location.origin}/api/public/calendar/${token}/redacted.ics`
}

type RevealedUrls = {
  full: string
  redacted: string
}

export function CalendarFeedSection() {
  const { t } = useTranslation(['auth', 'common'])
  const toast = useToast()
  const confirm = useConfirm()
  const { busy, error, setError, run } = useAction()
  const [status, setStatus] = useState<CalendarFeedStatus | null>(null)
  const [revealed, setRevealed] = useState<RevealedUrls | null>(null)

  useEffect(() => {
    void run(async () => {
      setStatus(await api.getCalendarFeed())
    }, t('auth:calendarFeedLoadFailed'))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once
  }, [])

  function revealFromToken(token: string) {
    setRevealed({
      full: calendarFeedUrl(token),
      redacted: calendarFeedRedactedUrl(token),
    })
  }

  function onCreate() {
    void run(async () => {
      const created = await api.createCalendarFeed()
      setStatus(created)
      revealFromToken(created.token)
      toast(t('auth:calendarFeedCreated'))
    }, t('auth:calendarFeedCreateFailed'))
  }

  function onRotate() {
    void run(async () => {
      const ok = await confirm({
        title: t('auth:calendarFeedRotateTitle'),
        description: t('auth:calendarFeedRotateBody'),
        confirmLabel: t('auth:calendarFeedRotate'),
        danger: true,
      })
      if (!ok) return
      const rotated = await api.rotateCalendarFeed()
      setStatus(rotated)
      revealFromToken(rotated.token)
      toast(t('auth:calendarFeedRotated'))
    }, t('auth:calendarFeedRotateFailed'))
  }

  function onRevoke() {
    void run(async () => {
      const ok = await confirm({
        title: t('auth:calendarFeedRevokeTitle'),
        description: t('auth:calendarFeedRevokeBody'),
        confirmLabel: t('common:revoke'),
        danger: true,
      })
      if (!ok) return
      const next = await api.revokeCalendarFeed()
      setStatus(next)
      setRevealed(null)
      toast(t('auth:calendarFeedRevoked'))
    }, t('auth:calendarFeedRevokeFailed'))
  }

  return (
    <Section icon="calendar" title={t('auth:calendarFeed')}>
      <p className="muted small">{t('auth:calendarFeedLead')}</p>
      {error && <Alert onDismiss={() => setError(null)}>{error}</Alert>}
      {revealed && (
        <div className="stack">
          <SecretReveal
            icon="calendar"
            title={t('auth:calendarFeedUrlTitle')}
            secret={revealed.full}
            onDismiss={() => setRevealed(null)}
          >
            {t('auth:calendarFeedUrlHint')}
          </SecretReveal>
          <SecretReveal
            icon="share"
            title={t('auth:calendarFeedRedactedUrlTitle')}
            secret={revealed.redacted}
            onDismiss={() => setRevealed(null)}
          >
            {t('auth:calendarFeedRedactedUrlHint')}
          </SecretReveal>
        </div>
      )}
      {status == null ? (
        <p className="muted small">{busy ? t('common:loading') : null}</p>
      ) : status.active ? (
        <div className="stack">
          <p className="muted small">{t('auth:calendarFeedActiveHint')}</p>
          <div className="actions">
            <button type="button" className="btn" disabled={busy} onClick={onRotate}>
              <Icon name="share" />
              {t('auth:calendarFeedRotate')}
            </button>
            <button type="button" className="btn danger" disabled={busy} onClick={onRevoke}>
              <Icon name="trash" />
              {t('common:revoke')}
            </button>
          </div>
        </div>
      ) : (
        <div className="actions">
          <button type="button" className="btn primary" disabled={busy} onClick={onCreate}>
            <Icon name="calendar" />
            {t('auth:calendarFeedCreate')}
          </button>
        </div>
      )}
    </Section>
  )
}
