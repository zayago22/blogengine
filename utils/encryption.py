"""
BlogEngine - Utilidades de encriptación.
Encripta/desencripta credenciales de CMS y redes sociales con Fernet.
"""
from cryptography.fernet import Fernet

from config import get_settings


def get_fernet() -> Fernet:
    """Retorna instancia de Fernet con la clave configurada."""
    settings = get_settings()
    key = settings.fernet_key
    if not key:
        raise ValueError(
            "FERNET_KEY no configurada. Genera una con: "
            "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encriptar(texto: str) -> str:
    """Encripta un texto y retorna string base64."""
    if not texto:
        return ""
    f = get_fernet()
    return f.encrypt(texto.encode()).decode()


def desencriptar(texto_encriptado: str) -> str:
    """Desencripta un texto base64 y retorna el texto original."""
    if not texto_encriptado:
        return ""
    f = get_fernet()
    return f.decrypt(texto_encriptado.encode()).decode()


def generar_fernet_key() -> str:
    """Genera una nueva clave Fernet. Usar para configurar FERNET_KEY."""
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # Ejecutar directamente para generar una clave
    print("Nueva FERNET_KEY:")
    print(generar_fernet_key())
