"""Language selection components."""


def render_language_buttons(st, t, ensure_language, get_language, set_language, prefix="lang"):
    ensure_language()
    current_language = get_language()
    with st.container():
        col_en, col_ro = st.columns(2)
        with col_en:
            if st.button(
                t("language.en"),
                type="primary" if current_language == "en" else "secondary",
                key=f"{prefix}_en",
                use_container_width=True,
            ):
                if current_language != "en":
                    set_language("en")
                    st.rerun()
        with col_ro:
            if st.button(
                t("language.ro"),
                type="primary" if current_language == "ro" else "secondary",
                key=f"{prefix}_ro",
                use_container_width=True,
            ):
                if current_language != "ro":
                    set_language("ro")
                    st.rerun()


def render_language_selector(st, t, ensure_language, get_language, set_language):
    render_language_buttons(st, t, ensure_language, get_language, set_language, "lang")


__all__ = [
    "render_language_buttons",
    "render_language_selector",
]

