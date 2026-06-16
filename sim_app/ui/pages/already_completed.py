"""Already-completed participant page."""


def render_already_completed_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.title(t("already_completed.title"))
    st.info(t("already_completed.body"))
    if ctx.repeat_scenario_dev_mode and st.button(t("already_completed.button"), type="primary"):
        ctx.start_new_scenario()
        st.rerun()


__all__ = [
    "render_already_completed_page",
]

