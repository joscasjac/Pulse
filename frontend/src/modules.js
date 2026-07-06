// Config-driven list views for the standalone Pulse module doctypes.
export const MODULES = {
  okrs: {
    title: 'OKRs', doctype: 'Pulse Objective',
    columns: [
      { key: 'objective_name', label: 'Objective', primary: true },
      { key: 'quarter', label: 'Quarter' },
      { key: 'objective_owner', label: 'Owner' },
      { key: 'category', label: 'Category', type: 'badge' },
      { key: 'progress', label: 'Progress', type: 'percent' },
      { key: 'confidence', label: 'Confidence', type: 'percent' },
    ],
  },
  risks: {
    title: 'Risks', doctype: 'Pulse Risk',
    columns: [
      { key: 'risk_title', label: 'Risk', primary: true },
      { key: 'project', label: 'Project' },
      { key: 'risk_level', label: 'Level', type: 'badge' },
      { key: 'status', label: 'Status', type: 'badge' },
      { key: 'risk_owner', label: 'Owner' },
      { key: 'risk_score', label: 'Score' },
    ],
  },
  meetings: {
    title: 'Meetings', doctype: 'Pulse Meeting',
    columns: [
      { key: 'title', label: 'Meeting', primary: true },
      { key: 'project', label: 'Project' },
      { key: 'date', label: 'Date' },
      { key: 'organizer', label: 'Organizer' },
      { key: 'status', label: 'Status', type: 'badge' },
    ],
  },
  portfolio: {
    title: 'Portfolio', doctype: 'Pulse Portfolio',
    columns: [
      { key: 'portfolio_name', label: 'Portfolio', primary: true },
      { key: 'owner', label: 'Owner' },
      { key: 'description', label: 'Description' },
    ],
  },
  retros: {
    title: 'Retrospectives', doctype: 'Pulse Retrospective',
    columns: [
      { key: 'title', label: 'Retro', primary: true },
      { key: 'project', label: 'Project' },
      { key: 'sprint', label: 'Sprint' },
      { key: 'date_held', label: 'Date' },
      { key: 'facilitator', label: 'Facilitator' },
      { key: 'overall_sentiment', label: 'Sentiment', type: 'badge' },
    ],
  },
  timesheets: {
    title: 'Timesheets', doctype: 'Pulse Timesheet',
    columns: [
      { key: 'user', label: 'User', primary: true },
      { key: 'week_starting', label: 'Week' },
      { key: 'total_hours', label: 'Hours' },
      { key: 'status', label: 'Status', type: 'badge' },
      { key: 'approved_by', label: 'Approved By' },
    ],
  },
  documents: {
    title: 'Documents', doctype: 'Pulse Document',
    columns: [
      { key: 'title', label: 'Title', primary: true },
      { key: 'project', label: 'Project' },
      { key: 'is_published', label: 'Published', type: 'check' },
    ],
  },
}
