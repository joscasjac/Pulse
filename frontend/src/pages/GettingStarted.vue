<template>
  <div class="getting-started">
    <header><h1>Get started with Pulse</h1><p class="text-muted">Set up one project, bring in your team, and start delivering work.</p></header>
    <ol>
      <li><h2>Create a project</h2><p>Open Projects and choose New project. Give it a clear name and a short project key. To start from a sale, expand Create delivery work from CRM or sales and select an existing submitted Sales Order, CRM Deal, or Opportunity.</p><RouterLink to="/projects">Open Projects →</RouterLink></li>
      <li><h2>Bring in your team</h2><p>From a project’s actions menu, choose Manage team. Administrators can add existing users, invite new team members, transfer ownership, and review offboarding. Removing project membership and disabling an ERP account are separate actions.</p></li>
      <li><h2>Add or import tasks</h2><p>Open the project and use New work item to add titles inline. Open a task for its description, dates, assignees, and other details. For a CSV file, choose Import / export tasks from the project’s actions menu, download the template, then preview your file before importing. A blank name creates a task; an existing task ID updates it.</p></li>
      <li><h2>Choose how you work</h2><p>Switch between List, Board, Calendar, Table, and Timeline in the task toolbar. Filter the tasks, choose visible columns, and save a view for work you revisit. Calendar dates and timeline bars use the same native task dates.</p><RouterLink to="/views">Open saved views →</RouterLink></li>
      <li><h2>Set your project’s rules</h2><p>Task settings let administrators configure statuses, task types, and fields required at specific stages. When a stage requires approval, request a review from another team member before moving the task there. Updating the reviewed content requires a fresh approval.</p></li>
      <li><h2>Share progress with clients or vendors</h2><p>Open a task’s External collaboration section and grant an existing external account access. External users receive a separate shared-work page with task title, status, dates, and an external discussion. Internal descriptions, attachments, and comments stay in the team workspace.</p></li>
      <li><h2>Keep reminders and automations reliable</h2><p>Administrators configure reminder days and email notifications in Pulse Settings. Delivery also needs a working ERP outgoing account, scheduler, workers, and the recipient’s notification preferences. Quest Automations can create and update work through permission-checked Pulse actions; inspect failed runs before retrying.</p><a href="/app/pulse-settings">Open Pulse Settings →</a></li>
      <li><h2>Document repeatable work</h2><p>Create project pages for briefs, specifications, and decisions. Link related tasks. Mark a project as a reusable template from its Business details to create a new project with its task structure.</p><RouterLink to="/documents">Open Pages →</RouterLink></li>
    </ol>
  </div>
</template>
<style scoped>
.getting-started{max-width:900px;margin:0 auto;padding:24px}.getting-started h1{font-size:24px;font-weight:600}.getting-started header p{margin-top:8px}.getting-started ol{padding-left:24px;margin-top:28px}.getting-started li{padding:0 0 24px 8px}.getting-started h2{font-size:16px;font-weight:600;margin-bottom:8px}.getting-started p{font-size:14px;line-height:1.7;max-width:72ch}.getting-started a{display:inline-block;margin-top:8px;color:var(--text-color,#202124);text-decoration:underline;text-underline-offset:3px}
</style>
