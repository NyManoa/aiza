"""Erreurs du domaine (traduites en codes HTTP par la couche API)."""


class NotFoundError(LookupError):
    """Ressource (pcode, lieu…) inconnue."""
