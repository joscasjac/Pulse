"""Sprint closure is an explicit planning decision, never an automatic date change."""


def auto_close_sprints():
    # Retained as a no-op for existing scheduler configurations. Managers choose
    # backlog/next/retain through planning.close_sprint; dates do not imply done.
    return
