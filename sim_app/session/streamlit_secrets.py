"""Install Streamlit secrets as the host adapter for framework-neutral infra."""

from sim_app.infra.secrets import configure_secret_provider


def configure_from_streamlit(secrets):
    def provider(name):
        value = secrets.get(name)
        if value is not None:
            return value
        for section_name in ("prolific", "auth", "admin", "supabase"):
            section = secrets.get(section_name)
            if section and section.get(name) is not None:
                return section.get(name)
        return None

    configure_secret_provider(provider)


__all__ = ["configure_from_streamlit"]
