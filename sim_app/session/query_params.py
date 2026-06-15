"""URL query parameter helpers."""

import streamlit as st


def get_query_param(name):
    try:
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value


def set_query_param(name, value):
    try:
        st.query_params[name] = value
    except Exception:
        st.experimental_set_query_params(**{name: value})

    script = f"""
<script>
(function() {{
  try {{
    var url = new URL(window.top.location.href);
    url.searchParams.set({name!r}, {value!r});
    window.top.history.replaceState({{}}, "", url.toString());
  }} catch (e) {{}}
}})();
</script>
"""
    st.components.v1.html(script, height=1)


def clear_query_param(name):
    try:
        if name in st.query_params:
            del st.query_params[name]
    except Exception:
        params = st.experimental_get_query_params()
        params.pop(name, None)
        st.experimental_set_query_params(**params)


__all__ = [
    "clear_query_param",
    "get_query_param",
    "set_query_param",
]
