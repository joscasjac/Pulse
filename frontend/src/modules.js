// Config-driven list views for the standalone Pulse module doctypes.
// Labels are getters so they translate after translations load (this module is imported before mount).
import { __ } from '@/translation'

export const MODULES = {
  okrs: {
    get title() { return __('OKRs') }, doctype: 'Pulse Objective',
    columns: [
      { key: 'objective_name', get label() { return __('Objective') }, primary: true },
      { key: 'quarter', get label() { return __('Quarter') } },
      { key: 'objective_owner', get label() { return __('Owner') } },
      { key: 'category', get label() { return __('Category') }, type: 'badge' },
      { key: 'progress', get label() { return __('Progress') }, type: 'percent' },
      { key: 'confidence', get label() { return __('Confidence') }, type: 'percent' },
    ],
  },
  risks: {
    get title() { return __('Risks') }, doctype: 'Pulse Risk',
    columns: [
      { key: 'risk_title', get label() { return __('Risk') }, primary: true },
      { key: 'project', get label() { return __('Project') } },
      { key: 'risk_level', get label() { return __('Level') }, type: 'badge' },
      { key: 'status', get label() { return __('Status') }, type: 'badge' },
      { key: 'risk_owner', get label() { return __('Owner') } },
      { key: 'risk_score', get label() { return __('Score') } },
    ],
  },
  meetings: {
    get title() { return __('Meetings') }, doctype: 'Pulse Meeting',
    columns: [
      { key: 'title', get label() { return __('Meeting') }, primary: true },
      { key: 'project', get label() { return __('Project') } },
      { key: 'date', get label() { return __('Date') } },
      { key: 'organizer', get label() { return __('Organizer') } },
      { key: 'status', get label() { return __('Status') }, type: 'badge' },
    ],
  },
  portfolio: {
    get title() { return __('Portfolio') }, doctype: 'Pulse Portfolio',
    columns: [
      { key: 'portfolio_name', get label() { return __('Portfolio') }, primary: true },
      { key: 'owner', get label() { return __('Owner') } },
      { key: 'description', get label() { return __('Description') } },
    ],
  },
  retros: {
    get title() { return __('Retrospectives') }, doctype: 'Pulse Retrospective',
    columns: [
      { key: 'title', get label() { return __('Retro') }, primary: true },
      { key: 'project', get label() { return __('Project') } },
      { key: 'sprint', get label() { return __('Sprint') } },
      { key: 'date_held', get label() { return __('Date') } },
      { key: 'facilitator', get label() { return __('Facilitator') } },
      { key: 'overall_sentiment', get label() { return __('Sentiment') }, type: 'badge' },
    ],
  },
  timesheets: {
    get title() { return __('Timesheets') }, doctype: 'Pulse Timesheet',
    columns: [
      { key: 'user', get label() { return __('User') }, primary: true },
      { key: 'week_starting', get label() { return __('Week') } },
      { key: 'total_hours', get label() { return __('Hours') } },
      { key: 'status', get label() { return __('Status') }, type: 'badge' },
      { key: 'approved_by', get label() { return __('Approved By') } },
    ],
  },
  documents: {
    get title() { return __('Documents') }, doctype: 'Pulse Document',
    columns: [
      { key: 'title', get label() { return __('Title') }, primary: true },
      { key: 'project', get label() { return __('Project') } },
      { key: 'is_published', get label() { return __('Published') }, type: 'check' },
    ],
  },
}
